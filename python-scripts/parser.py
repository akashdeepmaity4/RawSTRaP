"""Send source text to a CSV-producing API and persist the returned records.

API contract
------------
The endpoint accepts a JSON POST body shaped like ``{"text": "..."}`` and
returns either CSV text directly or JSON containing that text in a ``csv``,
``content``, or ``text`` field. Configure the endpoint with
``RAWSTRAP_API_URL``; an optional bearer token can be supplied in
``RAWSTRAP_API_KEY``. No UI code or third-party packages are required.
"""

from __future__ import annotations

import csv
from contextlib import closing
import io
import json
import os
import sqlite3
import urllib.error
import urllib.request
import unicodedata
import uuid
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV_DIR = PROJECT_ROOT / "temp-csv"
DEFAULT_DATABASE = PROJECT_ROOT / "database.db"
TABLE_NAME = "parsed_records"
API_TIMEOUT_SECONDS = 30

pre_payload = "use the prompt after the next : as source to follow the instructions. the instructions are to take the source, and convert it into csv. use your discretion to make sense of the document. if the source is split, make sub csv tuples with Null,Null,Null,... to separate them and if a certain portion is baseless, try to make sense of it or skip the portion and move ahead. avoid any regex, latex or katex or any commands. avoid any queries. treat the source as string and nothing else"


def sanitize_source_text(source_text: str) -> str:
	"""Normalize text and remove commas, backslashes, non-ASCII, and controls."""
	normalized = source_text.replace("\r\n", "\n").replace("\r", "\n")
	cleaned = "".join(
		character
		for character in normalized
		if character.isascii()
		and character not in {",", "\\"}
		and (character in "\n\t" or unicodedata.category(character) != "Cc")
	)
	return cleaned.strip()


def prepare_provider_payload(source: str) -> str:
	"""Sanitize source text and prepend the configured prompt prefix."""
	source = sanitize_source_text(source)
	if not source:
		raise ValueError("Source text must not be empty.")
        # hehe
	payload = pre_payload + source
	return payload


def send_payload_to_api(
	source_text: str,
	*,
	endpoint_url: str | None = None,
	api_key: str | None = None,
	timeout: int = API_TIMEOUT_SECONDS,
) -> str:
	"""POST source text to the configured endpoint and return its response body."""
	source_text = sanitize_source_text(source_text)
	if not source_text.strip():
		raise ValueError("Source text must not be empty.")

	endpoint = endpoint_url or os.environ.get("RAWSTRAP_API_URL")
	if not endpoint:
		raise ValueError("Set RAWSTRAP_API_URL or provide endpoint_url.")
	if not endpoint.startswith(("https://", "http://")):
		raise ValueError("API endpoint must use HTTP or HTTPS.")

	key = api_key if api_key is not None else os.environ.get("RAWSTRAP_API_KEY")
	headers = {
		"Accept": "text/csv, application/json",
		"Content-Type": "application/json; charset=utf-8",
	}
	if key:
		headers["Authorization"] = f"Bearer {key}"

	request = urllib.request.Request(
		endpoint,
		data=json.dumps({"text": source_text}).encode("utf-8"),
		headers=headers,
		method="POST",
	)
	try:
		with urllib.request.urlopen(request, timeout=timeout) as response:
			return response.read().decode("utf-8-sig")
	except urllib.error.HTTPError as error:
		raise RuntimeError(f"API returned HTTP {error.code}.") from error
	except urllib.error.URLError as error:
		raise RuntimeError(f"Could not reach API endpoint: {error.reason}") from error


def extract_csv_content(response_body: str) -> str:
	"""Extract CSV text from a raw CSV response or the documented JSON envelope."""
	try:
		payload: Any = json.loads(response_body)
	except json.JSONDecodeError:
		payload = None

	if isinstance(payload, str):
		csv_content = payload
	elif isinstance(payload, Mapping):
		csv_content = next(
			(payload[key] for key in ("csv", "content", "text") if key in payload),
			None,
		)
	elif payload is None:
		csv_content = response_body
	else:
		csv_content = None

	if not isinstance(csv_content, str) or not csv_content.strip():
		raise ValueError("API response must contain non-empty CSV text.")
	return csv_content


def parse_csv_content(csv_content: str) -> list[dict[str, str]]:
	"""Parse and validate CSV headers and records into dictionaries."""
	reader = csv.DictReader(io.StringIO(csv_content, newline=""))
	if not reader.fieldnames:
		raise ValueError("CSV must include a header row.")

	headers = [header.strip() if header is not None else "" for header in reader.fieldnames]
	if any(not header for header in headers):
		raise ValueError("CSV headers must not be empty.")
	if len(set(headers)) != len(headers):
		raise ValueError("CSV headers must be unique.")

	records: list[dict[str, str]] = []
	for line_number, row in enumerate(reader, start=2):
		if None in row or any(value is None for value in row.values()):
			raise ValueError(f"CSV row {line_number} has a different number of fields than its header.")
		records.append({header: row[original] for header, original in zip(headers, reader.fieldnames)})
	return records


def write_csv_file(csv_content: str, output_dir: str | Path = DEFAULT_CSV_DIR) -> Path:
	"""Write raw CSV text to a unique UTF-8 file and return its path."""
	output_path = Path(output_dir)
	output_path.mkdir(parents=True, exist_ok=True)
	filename = f"parsed-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:8]}.csv"
	csv_path = output_path / filename
	csv_path.write_text(csv_content, encoding="utf-8", newline="")
	return csv_path


def save_records_to_sqlite(
	source_text: str,
	records: list[dict[str, str]],
	database_path: str | Path = DEFAULT_DATABASE,
) -> int:
	"""Save parsed CSV rows transactionally as JSON payloads in SQLite."""
	database = Path(database_path)
	database.parent.mkdir(parents=True, exist_ok=True)
	created_at = datetime.now(timezone.utc).isoformat()

	with closing(sqlite3.connect(database)) as connection:
		with connection:
			connection.execute(
				f"""CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					source_text TEXT NOT NULL,
					row_number INTEGER NOT NULL,
					record_json TEXT NOT NULL,
					created_at TEXT NOT NULL
				)"""
			)
			connection.executemany(
				f"""INSERT INTO {TABLE_NAME}
					(source_text, row_number, record_json, created_at)
					VALUES (?, ?, ?, ?)""",
				[
					(source_text, row_number, json.dumps(record, ensure_ascii=False), created_at)
					for row_number, record in enumerate(records, start=1)
				],
			)
	return len(records)


def run_pipeline(
	source_text: str,
	*,
	endpoint_url: str | None = None,
	api_key: str | None = None,
	output_dir: str | Path = DEFAULT_CSV_DIR,
	database_path: str | Path = DEFAULT_DATABASE,
	api_caller: Callable[[str], str] | None = None,
) -> dict[str, Any]:
	"""Run text→API→CSV transfer→parse→SQLite save, returning output metadata.

	``api_caller`` is an optional dependency-injection hook for tests and
	alternate API adapters; it receives source text and returns a response body.
	"""
	source_text = sanitize_source_text(source_text)
	if not source_text:
		raise ValueError("Source text must not be empty.")

	if api_caller is None:
		response_body = send_payload_to_api(
			source_text,
			endpoint_url=endpoint_url,
			api_key=api_key,
		)
	else:
		response_body = api_caller(source_text)

	csv_content = extract_csv_content(response_body)
	csv_path = write_csv_file(csv_content, output_dir)
	records = parse_csv_content(csv_content)
	saved_count = save_records_to_sqlite(source_text, records, database_path)
	return {"csv_path": csv_path, "record_count": saved_count, "records": records}
