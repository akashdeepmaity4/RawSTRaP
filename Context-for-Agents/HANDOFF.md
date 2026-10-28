# RawSTRaP Agent Handoff

Last reviewed: 2026-10-28

## Purpose

Continue work on RawSTRaP, a Python desktop app for preparing source text and turning CSV rows into SQLite records. Read this file with `context.md`, `guardrails.md`, and the active `anti-hallucination.md` before making changes.

## Active project rules

- `anti-hallucination.md` is active by repository-owner confirmation. Ground claims in code, tests, or current authoritative documentation. Distinguish implemented, tested, and proposed behavior.
- `guardrails.md` is in force. Do not edit it. Do not edit `readme.md` or `.gitignore` without the explicit `-sudo` override. Do not delete documentation. Do not run commands affecting paths outside the project root.
- Never request, print, log, commit, or intentionally persist API keys. Do not claim Python securely erases a key from memory.
- Provider model-list validation does not prove free generation, remaining quota, or an active session. Do not send prompts or source text to a provider without reviewing its current official API contract and billing implications.

## Verified stack and launch flow

- Python, Tkinter, Pillow, and SQLite. Install `requirements.txt` and launch with `python run.py` from the repository root.
- `run.py` presents a provider dropdown and masked API-key entry. It makes one non-generative provider model-list request, then passes the provider and key in process memory to `python-scripts/UI.py` if validation succeeds.
- The main UI offers Talk it out and Upload file. Typed text and uploaded content are sanitized before use.
- Uploads are limited to `.txt`, `.md`, `.rst`, `.csv`, `.tsv`, `.json`, `.xml`, `.html`, `.htm`, `.yaml`, `.yml`, and `.toml`. Files are read as UTF-8 with optional BOM and rejected on decoding errors or NUL bytes.
- Sanitization normalizes line endings, removes commas, backslashes, non-ASCII characters, and control characters other than tabs/newlines, and trims outer whitespace.
- `python-scripts/parser.py` defines `pre_payload = "lorem ipsum "`. Its `prepare_provider_payload(source)` sanitizes `source` and returns `payload = pre_payload + source`.
- In provider mode, pressing PROCESS stores the sanitized source in `self.source`, the prepared payload in `self.prepared_payload`, and displays that generation is not enabled. No generation request or source-text upload to a provider is implemented.
- There is no backend server in the repository. Preparation occurs in the desktop app. The owner selected direct-from-desktop provider calls for future generation but explicitly said not to add generation calls yet.
- The legacy generic parser path is used only when no provider is set. It uses `RAWSTRAP_API_URL`, sends source text to that generic endpoint, accepts CSV directly or in JSON `csv`, `content`, or `text`, writes a CSV under `temp-csv/`, validates it, and saves JSON row records into SQLite `parsed_records`. It does not use `pre_payload` and is not provider-aware.
- SQLite row fields are `source_text`, `row_number`, `record_json`, and UTC `created_at`. Do not infer other schema fields or promise an extraction schema.
- Pillow renders the artwork at 4x and downsamples with Lanczos. Tkinter Entry, Text, menu, and status controls remain native widgets.

## Current modules

- `run.py`: provider selection, key validation workflow, and UI handoff.
- `python-scripts/providers.py`: one-request, non-generative key checks for Google Gemini, OpenAI, xAI, Anthropic Claude, and Groq-hosted Llama. Review official docs before changing request details or making live calls.
- `python-scripts/UI.py`: landing screen, text/file input, sanitation, local provider payload preparation, generic pipeline dispatch.
- `python-scripts/parser.py`: `pre_payload`, sanitation, provider payload preparation, generic HTTP adapter, CSV handling, and parameterized SQLite writes.
- `python-scripts/ui_graphics.py`: Pillow-based supersampled artwork.
- `smoke_test.py`: offline printed smoke suite, ignored by Git under current rules. Provider validation is mocked.
- `requirements.txt`: Pillow dependency.

## Known gaps and next work

- Provider-specific generation and response parsing are not implemented. Do not route a selected provider key through `RAWSTRAP_API_URL`; that adapter is not provider-aware.
- Before adding generation, confirm provider/model, official request and response format, billing expectations, and failure handling. No live calls are authorized by the current implementation request.
- There is no agreed natural-language extraction schema. CSV headers define fields; rows are stored as JSON.
- The latest observed compile and smoke run was performed before the latest sanitation and payload-preparation edits. At that earlier run, compilation succeeded and all 13 smoke sub-tests passed; provider checks were mocked. These latest edits have not been tested yet.

## Suggested next steps

1. Run compile and offline smoke checks after the latest changes; report outcomes accurately.
2. Wait for owner approval and details before implementing any provider generation request.
3. Add offline tests for comma/backslash/non-ASCII sanitation, payload concatenation, and text-document upload validation when requested.
4. Keep this handoff and `context.md` aligned with verified code. Do not edit the approved policy or guardrails without the required authorization.
