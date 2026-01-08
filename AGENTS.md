# AGENTS.md — Codex guardrails (Streamlit + SQLite Finance MVP)

This repo is developed with the Codex VS Code extension. These rules prevent data loss,
privacy leaks, and unintended scope creep.

## 0) Phase rule (spec-first)
- Until the user explicitly approves `PRD.md`, only documentation changes are allowed.
- During the spec-only phase, commits must use the `docs:` prefix.

## 1) Scope and workspace boundaries (hard rules)

### Repo-only file operations
- Only create/modify files inside the repo workspace.
- Never touch files outside the repo (no absolute paths, no sibling dirs).

### Forbidden internal paths (never edit directly)
- `.git/`
- `.venv/` (or any virtual environment folder)
- cache/state folders (`__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, etc.)

Running tools may create caches; do not edit/commit them.

## 2) Personal data and runtime artifacts (privacy + safety)

### Sensitive runtime directory: `data/` (host-side, gitignored)
Contains real personal data:
- `data/finance.db` and SQLite sidecars
- `data/csv_import/`
- `data/csv_export/`
- `data/db_backup/`
- `data/app_settings.db`

Hard rules:
- Never read, print, open, parse, or upload anything under `data/`.
- Never read/write/open any `*.db`, `*.db-wal`, `*.db-shm` under `data/`.
- Never read/print CSVs or backups under `data/`.

### Synthetic test data only
Allowed locations for synthetic data:
- `tests/fixtures/`
- `./.tmp_test/` (gitignored)
- In-memory SQLite (`:memory:`) for non-WAL tests

## 3) Command execution policy

### Allowed commands (safe)
- `pytest` / `python -m pytest`
- `ruff`, `black`, `mypy` only if already configured

### Requires explicit user approval
- Docker builds/containers (`docker`, `docker compose`)
- Any command touching real DBs under `data/`
- Bulk file generators/movers

### Never run destructive commands
- `rm -rf`, cleanup scripts, global installs
- Anything that modifies system config, SSH keys, or user directories

## 4) Mission
Implement the MVP described in `PRD.md` as a modular, readable Streamlit app backed by SQLite.

Priority order:
1) Correctness + consistency with `PRD.md`
2) Simplicity + readability
3) UI polish

Do not invent features.

## 5) Hard constraints (non-negotiable)
- Streamlit multipage UI.
- SQLite via Python `sqlite3` module.
- No saved analytics presets or reports beyond DB content (settings DB allowed for UI config).
- Edit/delete transactions one at a time (no bulk transaction edits).
- All SQL uses parameter placeholders (`?`), never string formatting.
- Use WAL + foreign keys:
  - `PRAGMA journal_mode=WAL;`
  - `PRAGMA foreign_keys=ON;`
- Store currency as integer cents:
  - `amount_cents INTEGER NOT NULL`, non-negative
  - UI/CSV amounts parsed to cents, 0-2 decimals, no signs, no commas
- Finance-domain text fields must already be normalized (lower(trim())); DB rejects non-normalized.
- Notes preserve case; empty/whitespace-only values are invalid if not NULL.
- Tags normalized and comma-free:
  - `tags(id, name UNIQUE)` with CHECKs for lower(trim()), non-empty, no commas
  - `transaction_tags(transaction_id, tag_id)` with PK(transaction_id, tag_id)
- Comparison engine is UI-agnostic (no Streamlit imports).

## 6) Repo structure (recommended)
Keep files small (<250–300 LOC each).

- `app.py`
- `src/`
  - `db.py`                (connect, PRAGMA, schema init, backup, settings DB)
  - `schema.sql`           (authoritative finance DB schema)
  - `types.py`             (Period/Group/Node dataclasses)
  - `amounts.py`           (parse/format amounts)
  - `csv_io.py`            (CSV import/export helpers)
  - `tags.py`              (tag upsert, tag assignment, tag queries)
  - `queries.py`           (SQL query builders, WHERE utilities)
  - `comparison_engine.py` (comparison logic; returns dataframe)
  - `plotting.py`          (Altair charts for compare page)
  - `ui_widgets.py`        (P1/P2/P3 helpers)
- `pages/`
  - `1_Home.py`
  - `2_Transactions.py`
  - `3_Import_Export.py`   (includes Backup)
  - `4_Manage_Values.py`
  - `5_Compare.py`
- `requirements.txt`
- `Dockerfile`
- `docker-compose.yml`
- `.gitignore` must ignore `data/`, `*.db*`, `.tmp_test/`

## 7) Configuration (host vs Docker)
Host-side repo uses `data/` (gitignored):
- `data/finance.db`
- `data/csv_import/`
- `data/csv_export/`
- `data/db_backup/`
- `data/app_settings.db`

Container convention: mount `./data` to `/data`.

Environment defaults:
- `FINANCE_DB_PATH` default `/data/finance.db`
- `FINANCE_CSV_IMPORT_DIR` default `/data/csv_import`
- `FINANCE_CSV_EXPORT_DIR` default `/data/csv_export`
- `FINANCE_DB_BACKUP_DIR` default `/data/db_backup`

Settings DB (`/data/app_settings.db`) persists:
- last-used DB
- recent DBs (max 3)
- theme (light/dark)
- import/export/backup dirs (editable in UI)

## 8) UI behavior requirements
- Follow `UI_BLUEPRINT.md` for patterns and page behavior.
- Prefer existing DB values; creation only in explicit contexts.
- Confirm destructive operations.
- Transactions list supports column hide/show and ordering; date filter uses `date_application`.

## 9) CSV import/export
Import:
- Semicolon-separated CSV with headers trimmed and case-insensitive.
- Required columns: `amount`, `category`, at least one of `date_payment`/`date_application`,
  and at least one of `payer`/`payee`.
- Amounts: dot decimal only; 0-2 fractional digits; no commas, no signs.
- Tags: comma-separated; no escaping; tag names cannot contain commas.
- Normalize inputs; empty/whitespace-only -> NULL for nullable fields.
- Validate all rows; insert in a single transaction; abort on any invalid row.

Export:
- Date range required; date-field selector (`date_application` default).
- Optional filters for payer/payee/category/subcategory/payment_type/tags.
- Tags filter uses ANY semantics; untagged tx excluded if tags selected.
- Include both date columns and a `tags` column.

## 10) Comparison logic
Implement exactly as specified in `PRD.md` (periods, groups, role vs matched-only,
slice modes, TagMatch ANY/ALL, node outputs).

## 11) Testing policy
- Use synthetic data only (`tests/fixtures`, `./.tmp_test/`, or `:memory:`).
- Use file-backed DBs under `./.tmp_test/` for WAL/backup tests.
- Never open or read any DB/CSV under `data/`.

## 12) Commits
- Commit early, commit often.
- Allowed prefixes: `chore:`, `feat:`, `fix:`, `refactor:`, `analytics:`, `docs:`, `test:`
- During spec-only phase: `docs:` commits only.
