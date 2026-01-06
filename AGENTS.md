# AGENTS.md — Codex build instructions (Streamlit + SQLite Finance MVP)

This repository is developed with the **Codex VS Code extension** (side-panel agent).
These rules exist to prevent data loss, privacy leaks, and “helpful” mistakes.

---

## 1) Scope and workspace boundaries (hard rules)

### Repo-only file operations
- The agent must **only** create/modify files **inside the current VS Code workspace folder** (the repo root and its subfolders).
- The agent must **never** create, modify, move, or delete files outside the repo (e.g., `~/.config`, `~/Downloads`, sibling folders, absolute system paths).

If an action would require touching anything outside the repo:
- Stop and explain what the user should do manually (with explicit file paths/commands),
- or propose a repo-internal alternative.

### Forbidden internal paths (never edit directly)
The agent must not edit, delete, or “clean up”:
- `.git/`
- `.venv/` (or any virtual environment folder)
- cache/state folders (`__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, etc.)

Note: running Python tools may create cache folders; the agent must simply not edit/commit them.

---

## 2) Personal data and runtime artifacts (privacy + safety)

### Sensitive runtime directory: `data/` (host-side)
This repo uses a host directory `data/` (gitignored) that contains real personal data:
- `data/finance.db` and SQLite sidecars
- `data/csv_import/`
- `data/csv_export/`
- `data/db_backup/`

**Hard rule:** the agent must never read, print, open, parse, or upload any personal files from `data/`.

#### Database files are untouchable
The agent must never read/write/open/print/copy:
- any `*.db`, `*.db-wal`, `*.db-shm` under `data/`
- any `finance.db` anywhere in the repo

If a task involves schema/migrations:
- operate only on schema scripts and application code
- use an **in-memory** SQLite DB (`:memory:`) or a synthetic temporary DB in `./.tmp_test/` for tests

#### CSV imports/exports/backups are untouchable
The agent must never read/print any personal transaction exports/imports/backups:
- any `*.csv`, `*.xlsx`, `*.json` under `data/`
- any files under `data/csv_import/`, `data/csv_export/`, `data/db_backup/`

#### Exception: synthetic test data is allowed
The agent may create and use **synthetic** datasets for testing only under:
- `tests/fixtures/` (small, fake data with no personal content)
- `./.tmp_test/` (temporary test DBs/files created by tests; should be gitignored)

### Do not echo personal data into chat
Even if asked for debugging:
- do not paste real transaction rows, real CSV contents, or DB contents into chat.
- demonstrate behavior with synthetic examples only.

---

## 3) Command execution policy

The agent should behave conservatively: code changes first, execution second.

### Allowed commands (generally safe)
The agent may run these if needed for verification:
- `pytest` / `python -m pytest`
- `ruff`, `black`, `mypy` only if they are already configured in the repo

### Commands requiring explicit user approval
The agent must ask before:
- running Docker builds/containers (`docker`, `docker compose`)
- running any command that would open or migrate a real DB under `data/`
- running scripts that generate or move files in bulk

### Never run destructive commands
Do not run:
- `rm -rf`, cleanup scripts, global package installs
- anything that modifies system config, SSH keys, or user directories

---

## 4) Mission
Implement the MVP described in PRD.md as a modular, readable Streamlit app backed by SQLite.

Priority order:
1) Correctness + consistency with PRD.md
2) Simplicity + readability (no “framework inside the framework”)
3) UI polish (last)

Do not invent new features.

---

## 5) Hard constraints (non-negotiable)
- Use Streamlit multipage UI.
- Use SQLite via Python `sqlite3` module.
- No saved/persistent presets beyond what is stored in the database.
- Edit/delete transactions **one at a time** (no bulk edit).
- All SQL must use parameter placeholders only (`?`), never string formatting.
- Use WAL mode + foreign keys:
  - `PRAGMA journal_mode=WAL;`
  - `PRAGMA foreign_keys=ON;`
- Store currency as integer cents:
  - DB column is `amount_cents INTEGER NOT NULL`
  - derived from CSV `amount` with proper decimal parsing/rounding
- Tags must be **normalized**:
  - `tags(id, name UNIQUE)`
  - `transaction_tags(transaction_id, tag_id)` with PK(transaction_id, tag_id)
- Comparison engine must be UI-agnostic (no Streamlit imports).

---

## 6) Repo structure (recommended)
Keep files small (<250–300 LOC each).

- `app.py`
- `src/`
  - `db.py`                (connect, PRAGMA, schema init, backup)
  - `schema.sql`           (authoritative schema)
  - `types.py`             (Period/Group/Node dataclasses)
  - `csv_io.py`            (parse/validate CSV, import/export helpers)
  - `tags.py`              (tag upsert, set tags on tx, tag queries)
  - `queries.py`           (SQL query builders, WHERE utilities)
  - `comparison_engine.py` (compute cube results; returns dataframe)
  - `plotting.py`          (Altair charts for comparison page)
  - `ui_widgets.py`        (typeahead/select helpers)
- `pages/`
  - `1_Home.py`
  - `2_Transactions.py`
  - `3_Import_Export.py`
  - `4_Manage_Values.py`
  - `5_Compare.py`
  - `6_Backup.py`
- `requirements.txt`
- `Dockerfile`
- `docker-compose.yml`
- `.gitignore` (must ignore `data/`, `*.db*`, `.tmp_test/`)

---

## 7) Configuration (host vs Docker)
Host-side repo uses `data/` (gitignored) with:
- `data/finance.db`
- `data/csv_import/`
- `data/csv_export/`
- `data/db_backup/`

Docker convention (inside container) may mount host `./data` to container `/data`.

Support env defaults:
- `FINANCE_DB_PATH` default `/data/finance.db`
- `FINANCE_CSV_IMPORT_DIR` default `/data/csv_import`
- `FINANCE_CSV_EXPORT_DIR` default `/data/csv_export`
- `FINANCE_DB_BACKUP_DIR` default `/data/db_backup`

UI allows overriding per session (store in `st.session_state`).

---

## 8) UI behavior requirements
- Prefer selecting from existing DB values.
- Provide “Add new …” options where appropriate.
- Confirm destructive operations (delete transaction, delete value, delete tag, backups).

### “Fuzzy search” selectors (MVP)
Implement typeahead pattern:
1) `st.text_input("Search …")`
2) filter list by substring (case-insensitive)
3) `st.selectbox` over filtered list

---

## 9) CSV import/export
Import:
- semicolon-separated
- required: `date` (YYYY-MM-DD), `amount`, `category`
- optional: payer, payee, subcategory, notes, tags
- normalize: trim; empty→NULL; lowercase category/subcategory/tags
- tags split by comma `,`, trim/lowercase/dedupe
- validate strictly; abort on any invalid row; insert in one transaction

Export:
- date range required; optional payer/payee/category/subcategory/tags filters
- include `tags` column reconstructed from join tables
- Streamlit download; optionally save to `FINANCE_CSV_EXPORT_DIR`

---

## 10) Comparison logic (implement exactly)
(Keep as specified in PRD.md: periods/groups, role vs matched_only, AND/OR node selection, TagMatch ANY/ALL in AND mode, output dataframe, grouped-bar plots.)

---

## 11) Implementation plan (commit early, commit often)
Commit to `main` frequently. Each commit must leave the app runnable.

Allowed prefixes:
- `chore:`, `feat:`, `fix:`, `refactor:`, `analytics:`, `docs:`, `test:`

Never commit personal data. `.gitignore` must exclude:
- `data/`
- `*.db`, `*.db-wal`, `*.db-shm`
- `.tmp_test/`

If any personal files are already tracked, do **not** rewrite git history automatically; explain remediation steps.

---

## 12) Quality checks
- Use synthetic data for tests only.
- Create/open a fresh test DB (in-memory or `.tmp_test/`) and verify:
  - CRUD + tags
  - CSV import/export on synthetic CSV
  - backup code path (to a synthetic target path)
  - comparison logic outputs and plots
