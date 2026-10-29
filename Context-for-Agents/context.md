# Context, Architecture, and Workflow

## 1. Project Overview

RawSTRaP (Raw Source Text to Relation Parser) is a Python desktop application built with Tkinter, Pillow, and SQLite. It has a provider key validation flow and a text sanitation and CSV-to-SQLite pipeline. Provider-specific CSV generation is implemented for the supported providers.

## 2. Repository Structure

```text
RawSTRaP/
|-- run.py                         # Provider selection, key check, UI handoff
|-- requirements.txt               # Pillow dependency
|-- smoke_test.py                  # Local offline smoke suite (ignored by Git)
|-- python-scripts/
|   |-- UI.py                      # Main UI, source input, workflow screens, preview
|   |-- parser.py                  # Sanitation, payload preparation, API and CSV/SQLite pipeline
|   |-- providers.py               # Provider key checks and CSV generation adapters
|   `-- ui_graphics.py             # Supersampled Pillow artwork
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
- Provider prompt: `python-scripts/parser.py` defines `pre_payload` as the instruction prefix for converting source text into CSV. It asks the provider to handle edge cases and multiple topics/items with separate rows when appropriate, use surrounding context to interpret unclear material without inventing facts, use `Null` for missing or unresolved values, and return CSV. `prepare_provider_payload(source)` sanitizes the source and appends it to that prefix.
- Current UI behavior: after key validation, the app selects a text-generation model from the provider's model list. Pressing PROCESS sanitizes the source, builds `self.prepared_payload`, asks for database and table names, and requires the user to confirm they verified free access for the selected key/model before sending. The app cannot independently verify billing tier; declining the confirmation sends nothing.
- After successful processing, stage five offers CSV preview, Open File Location, and back navigation. Open File Location opens the directory containing the SQLite database and leaves the app on stage five. Preview opens stage six, a resizable read-only table of CSV rows and columns with scrollbars and a Back to Results control.
- Provider pipeline: `providers.py` sends the prepared prompt to the selected provider and extracts generated CSV text. The UI saves the CSV under `temp-csv/`, validates it, and persists rows into a user-named SQLite table with TEXT columns based on the CSV headers.
- Legacy generic pipeline: when no provider is set, the UI can send source text to `RAWSTRAP_API_URL`. `parser.py` accepts CSV text directly or inside JSON `csv`, `content`, or `text`, writes CSV under `temp-csv/`, validates rows, and stores each CSV row as JSON in SQLite table `parsed_records`. This generic path does not use the selected provider or prepend the provider prompt prefix.
- SQLite uses parameterized values. The generic path stores `source_text`, `row_number`, `record_json`, and UTC `created_at`; the provider path creates table columns from CSV headers.

There is no backend server in this repository. Source preparation and SQLite writes run locally in the desktop app. After the GUI free-access confirmation, a generation request is sent directly from the desktop app to the selected provider. API usage may be billable if the user's verification is incorrect; model-list validation cannot confirm cost status.

## 4. Current Implementation Status

- `run.py` shows a welcome/provider selection screen, then a masked key entry screen. It performs key validation on a worker thread and opens the main UI on success. Back navigation returns to the preceding flow screen; the welcome-stage Exit button closes the app.
- `providers.py` implements one GET model-list request for each of five providers and maps common authentication, payment, rate-limit, network, and response errors. These requests are separate from generation.
- `UI.py` shows the post-validation landing screen, accepts typed text or supported UTF-8 plain-text documents, collects database/table names, gates generation behind the free-access confirmation, and provides stages five and six for result actions and CSV table preview.
- `providers.py` sends the provider prompt plus sanitized source to provider-specific text-generation endpoints and extracts CSV response text. The app selects a likely text model from the provider's available model list.
- `parser.py` retains a generic HTTP POST adapter plus CSV extraction, validation, file output, and SQLite persistence. The provider route saves the model CSV under `temp-csv/` and creates a SQLite table whose TEXT columns come from CSV headers. The exact headers are model-generated; no fixed extraction schema is guaranteed.
- `ui_graphics.py` draws smooth artwork through Pillow supersampling; Tkinter entry, text, menu, and status widgets remain native controls.
- `SQL-to-Python/python-func-for-sql.py` only contains a comment describing an intended helper role.
- `smoke_test.py` is an offline printed import smoke test, ignored by the current Git rules. It does not exercise live provider requests or the visual Tkinter workflow.

## 5. Guardrails for Further Work

- Read `HANDOFF.md`, `guardrails.md`, and `anti-hallucination.md` before changes. The latter is active by repository-owner confirmation.
- Do not edit `guardrails.md`. Follow the explicit `-sudo` override requirement for `readme.md` and `.gitignore`; do not delete documentation.
- Do not run commands affecting paths outside the repository root.
- Do not request, print, log, commit, or intentionally persist secrets. Do not send source text or prompts to a provider without verifying its current official API contract and considering billing consequences.
- Before changing generation, verify the provider/model request and response format, billing behavior, and failure handling. Do not treat model-list validation as proof of free or active generation access, and do not make live provider calls during development checks.
- Do not invent extraction columns or claim that natural-language extraction works. The current SQLite schema stores CSV row dictionaries as JSON.
- Keep the project small and use SQLite parameterized queries for values. Avoid introducing new infrastructure without an explicit requirement.
