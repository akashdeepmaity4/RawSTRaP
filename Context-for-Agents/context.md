# Context, Architecture, and Workflow

## 1. Project Overview

RawSTRaP (Raw Source Text to Relation Parser) is a Python desktop application built with Tkinter, Pillow, and SQLite. It has a provider key validation flow and a separate text sanitation and CSV-to-SQLite pipeline. Provider-specific text generation is not implemented.

## 2. Repository Structure

```text
RawSTRaP/
|-- run.py                         # Provider selection, key check, UI handoff
|-- requirements.txt               # Pillow dependency
|-- smoke_test.py                  # Local offline smoke suite (ignored by Git)
|-- python-scripts/
|   |-- UI.py                      # Main UI, source input, upload, dispatch guard
|   |-- parser.py                  # Sanitation, payload preparation, generic API and CSV/SQLite pipeline
|   |-- providers.py               # Non-generative provider key checks
|   `-- ui_graphics.py             # Supersampled Pillow artwork
|-- SQL-to-Python/
|   `-- python-func-for-sql.py     # Intended helper module; no implementation
|-- temp-csv/                      # Generated CSV destination
`-- Context-for-Agents/
    |-- context.md
    |-- guardrails.md
    |-- anti-hallucination.md
    `-- HANDOFF.md
```

The repository's `.gitignore` excludes generated files, environments, `temp-csv/`, `database.db`, and the smoke tests.

## 3. Technology and Data Flow

- Python desktop UI: Tkinter native controls with Pillow artwork rendered at four times target resolution and downsampled using Lanczos.
- Provider validation: one provider-specific, non-generative model-list GET for Google Gemini, OpenAI, xAI, Anthropic Claude, or Groq-hosted Llama. A model-list response does not establish that generation is free, available, or within quota.
- Credentials: the validated key is passed in process memory to the UI. The code does not intentionally write it to disk or logs. Do not claim secure erasure from memory.
- Source entry: users can type raw text or upload a plain-text document. Upload extensions are limited to `.txt`, `.md`, `.rst`, `.csv`, `.tsv`, `.json`, `.xml`, `.html`, `.htm`, `.yaml`, `.yml`, and `.toml`; files are decoded as UTF-8 (optional BOM) and rejected if they contain NUL bytes.
- Sanitation: `python-scripts/parser.py::sanitize_source_text` normalizes CRLF/CR line endings, removes commas, backslashes, non-ASCII characters, and control characters other than tabs/newlines, then trims outer whitespace.
- Prefix: `python-scripts/parser.py` defines `pre_payload = "lorem ipsum "`. `prepare_provider_payload(source)` sanitizes the source and returns the simple concatenation `payload = pre_payload + source`.
- Current UI behavior: when a provider is selected, pressing PROCESS sanitizes the source and prepares `self.prepared_payload` in memory. It displays that provider generation is not enabled. No prompt or source text is sent to the selected provider.
- Legacy generic pipeline: when no provider is set, the UI can send source text to `RAWSTRAP_API_URL`. `parser.py` accepts CSV text directly or inside JSON `csv`, `content`, or `text`, writes CSV under `temp-csv/`, validates rows, and stores each CSV row as JSON in SQLite table `parsed_records`. This generic path does not use the selected provider and does not prepend `pre_payload`.
- SQLite uses parameterized values. Rows retain `source_text`, `row_number`, `record_json`, and UTC `created_at`.

There is no backend server in this repository. The source preparation described above runs locally in the desktop app. The provider API, when generation is later implemented, would receive requests directly from the desktop app as instructed by the owner; no such generation request is implemented yet.

## 4. Current Implementation Status

- `run.py` shows a welcome/provider selection screen, then a masked key entry screen. It performs key validation on a worker thread and opens the main UI on success.
- `providers.py` implements one GET model-list request for each of five providers and maps common authentication, payment, rate-limit, network, and response errors. These requests are separate from generation.
- `UI.py` shows the post-validation landing screen, accepts typed text or supported UTF-8 plain-text documents, and applies sanitation before use. Provider mode currently prepares the prefixed payload locally and stops without making a generation call.
- `parser.py` also retains a generic HTTP POST adapter plus CSV extraction, validation, file output, and SQLite persistence. It does not define a natural-language extraction schema.
- `ui_graphics.py` draws smooth artwork through Pillow supersampling; Tkinter entry, text, menu, and status widgets remain native controls.
- `SQL-to-Python/python-func-for-sql.py` only contains a comment describing an intended helper role.
- `smoke_test.py` is an offline printed smoke suite, ignored by the current Git rules. Provider tests use mocks and make no live requests.

## 5. Guardrails for Further Work

- Read `HANDOFF.md`, `guardrails.md`, and `anti-hallucination.md` before changes. The latter is active by repository-owner confirmation.
- Do not edit `guardrails.md`. Follow the explicit `-sudo` override requirement for `readme.md` and `.gitignore`; do not delete documentation.
- Do not run commands affecting paths outside the repository root.
- Do not request, print, log, commit, or intentionally persist secrets. Do not send source text or prompts to a provider without verifying its current official API contract and considering billing consequences.
- Before implementing generation, clarify the provider/model choice, request and response format, billing behavior, and failure handling. Do not treat model-list validation as proof of free or active generation access.
- Do not invent extraction columns or claim that natural-language extraction works. The current SQLite schema stores CSV row dictionaries as JSON.
- Keep the project small and use SQLite parameterized queries for values. Avoid introducing new infrastructure without an explicit requirement.
