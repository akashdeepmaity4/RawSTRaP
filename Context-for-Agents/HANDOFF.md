# RawSTRaP Agent Handoff

Last reviewed: 2026-10-29

## Purpose

Continue work on RawSTRaP, a Python desktop app for preparing source text and turning CSV rows into SQLite records. Read this file with `context.md`, `guardrails.md`, and the active `anti-hallucination.md` before making changes.

## Active project rules

- `anti-hallucination.md` is active by repository-owner confirmation. Ground claims in code, tests, or current authoritative documentation. Distinguish implemented, tested, and proposed behavior.
- `guardrails.md` is in force. Do not edit it. Do not edit `readme.md` or `.gitignore` without the explicit `-sudo` override. Do not delete documentation. Do not run commands affecting paths outside the project root.
- Never request, print, log, commit, or intentionally persist API keys. Do not claim Python securely erases a key from memory.
- Provider model-list validation does not prove free generation, remaining quota, or an active session. Do not send prompts or source text to a provider without reviewing its current official API contract and billing implications.

## Verified stack and launch flow

- Python, Tkinter, Pillow, and SQLite. Install `requirements.txt` and launch with `python run.py` from the repository root.
- `run.py` presents a provider dropdown and masked API-key entry. It makes one non-generative provider model-list request, then passes the provider and key in process memory to the main UI if validation succeeds. The key screen can return to provider selection; the main UI can return to the key screen with the masked key repopulated.
- The main UI offers Talk it out and Upload file. Typed text and uploaded content are sanitized before use. After successful processing, stage five offers Preview File, Open File Location, and Go Back. Open File Location opens the directory containing the SQLite database and leaves the app on stage five; the directory is not opened automatically. Preview File opens stage six, a resizable read-only CSV table with horizontal and vertical scrolling and a Back to Results control. Back navigation preserves source text when returning from input/results to earlier workflow screens.
- Uploads are limited to `.txt`, `.md`, `.rst`, `.csv`, `.tsv`, `.json`, `.xml`, `.html`, `.htm`, `.yaml`, `.yml`, and `.toml`. Files are read as UTF-8 with optional BOM and rejected on decoding errors or NUL bytes.
- Sanitization normalizes line endings, removes commas, backslashes, non-ASCII characters, and control characters other than tabs/newlines, and trims outer whitespace.
- `python-scripts/parser.py` defines `pre_payload` as the provider instruction prefix for CSV conversion. It asks for contextual handling of edge cases and multiple items, separate rows where appropriate, consistent columns, no unsupported facts, and `Null` for missing or unresolved values. `prepare_provider_payload(source)` sanitizes `source` and appends it to the prefix.
- In provider mode, the key check selects a likely text-generation model from the provider's model list. Pressing PROCESS stores sanitized source in `self.source`, builds `self.prepared_payload`, asks for database and table names, and asks the user to confirm that they verified free access for the selected key/model. If declined, no request is sent. If confirmed, the payload is sent directly to the selected provider from the desktop app.
- The app cannot independently verify account billing tier. A mistaken free-access confirmation could allow billable API usage; model-list validation does not establish that a generation call is free.
- Provider responses are expected to contain CSV text. The app saves the response in `temp-csv/`, validates its headers/rows, creates a SQLite table with TEXT columns named from the CSV headers, and inserts the rows with parameterized values. It stores the database in the project root. On stage five the user can explicitly open the directory containing that database.
- There is no backend server in the repository. Preparation and provider calls occur directly from the desktop app.
- The legacy generic parser path is used only when no provider is set. It uses `RAWSTRAP_API_URL`, sends source text to that generic endpoint, accepts CSV directly or in JSON `csv`, `content`, or `text`, writes a CSV under `temp-csv/`, validates it, and saves JSON row records into SQLite `parsed_records`. It does not use `pre_payload` and is not provider-aware.
- SQLite row fields are `source_text`, `row_number`, `record_json`, and UTC `created_at`. Do not infer other schema fields or promise an extraction schema.
- Pillow renders the artwork at 4x and downsamples with Lanczos. Tkinter Entry, Text, menu, and status controls remain native widgets.

## Current modules

- `run.py`: provider selection, key validation workflow, and UI handoff/back navigation.
- `python-scripts/providers.py`: one-request, non-generative key checks for Google Gemini, OpenAI, xAI, Anthropic Claude, and Groq-hosted Llama. Review official docs before changing request details or making live calls.
- `python-scripts/UI.py`: landing and text/file input screens, back navigation, sanitation, local provider payload preparation, pipeline dispatch, stage-five result actions, stage-six read-only CSV table preview, and database-directory opening.
- `python-scripts/parser.py`: `pre_payload`, sanitation, provider payload preparation, generic HTTP adapter, CSV handling, and parameterized SQLite writes.
- `python-scripts/ui_graphics.py`: Pillow-based supersampled artwork.
- `smoke_test.py`: offline printed import smoke test, ignored by Git under current rules. Provider validation and generation are not exercised by this smoke test.
- `requirements.txt`: Pillow dependency.

## Known gaps and next work

- Provider-specific generation is implemented for the listed providers using their respective text endpoints. Do not make live provider calls during development checks. Before changing generation behavior, verify current provider/model request and response formats, billing expectations, and failure handling against official documentation. Do not route a selected provider key through `RAWSTRAP_API_URL`; that adapter remains separate and is not provider-aware.
- There is no agreed natural-language extraction schema. CSV headers define fields; rows are stored as JSON.
- On 2026-10-29, Python compilation of `run.py`, `smoke_test.py`, and `python-scripts/` succeeded, and `smoke_test.py` completed all four module-import checks. The stage-six table preview change was also compiled and the smoke test passed. No live provider calls were made. The smoke test required registering dynamically loaded modules in `sys.modules` for compatibility with the current Python `dataclasses` implementation.
- After updating Open File Location to open the SQLite database directory, `python-scripts/UI.py` compiled and all four offline module-import smoke checks passed. The GUI action was not manually exercised; no live provider calls were made.
- `git diff --check` passed for the changed UI files. A broader check reported pre-existing trailing whitespace in `python-scripts/ui_graphics.py`; that file was not changed as part of the UI-stage work.

## Suggested next steps

1. Add mocked generation-response and dynamic SQLite table checks without live provider requests.
2. Review the model-selection heuristic and free-access confirmation with the owner; the app cannot prove billing tier before sending.
3. Keep this handoff and `context.md` aligned with verified code. Do not edit the approved policy or guardrails without the required authorization.
