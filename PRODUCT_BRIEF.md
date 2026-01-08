# Product Brief

## Overview
Build a single-user Streamlit + SQLite personal finance dashboard for local use on a desktop host,
with occasional mobile access via browser (e.g., remote access into the desktop-hosted container).
The app focuses on clean CSV import/export, reliable transaction CRUD, comparison analytics, and
safe database backups.

## Target User and Context
- One user only, no shared accounts.
- Desktop-first UI; must remain usable on mobile browsers.
- Deployed locally (Docker optional); no cloud sync.

## Goals (MVP)
1. Import semicolon-separated CSV transactions with strict validation and atomic insert.
2. Export transactions to CSV with filters and a required date range.
3. Add, edit, and delete transactions one at a time, including tags.
4. Comparison engine with multiple periods and groups, correct inflow/outflow logic, and charts.
5. Manage values in bulk (rename/merge) for payer, payee, category, subcategory, payment_type, tags.
6. Back up the SQLite database to a configured directory.

## Non-goals
- Multi-user support or permissions.
- Cloud sync or external integrations (bank APIs).
- Budgets, recurring schedules, or forecasting.
- Bulk edit/delete of transactions in MVP.

## MVP Scope
### In Scope
- Streamlit multipage UI with pages for Home, Transactions, Import/Export (including Backup),
  Manage Values, and Compare.
- SQLite via Python sqlite3 with WAL and foreign keys enabled.
- Normalized tags (tags, transaction_tags).
- Amounts stored as integer cents only.
- Case-insensitive search; finance-domain values stored in lowercase (notes preserve case).
- Payer and payee must differ on every transaction (cannot be equal or both NULL).
- Settings DB to persist UI preferences (theme, recent DBs, configured directories).

### Out of Scope (Later)
- Multi-currency support.
- Preset filters or saved reports.
- Advanced analytics beyond the comparison engine.

## Constraints (Non-negotiable)
- Streamlit multipage app.
- SQLite via sqlite3 module only.
- No saved analytics presets or reports beyond database content; settings DB is allowed
  for UI/config only.
- SQL uses parameter placeholders only (?).
- PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON.
- amount_cents INTEGER NOT NULL; no float amounts stored.
- Tags normalized in tags and transaction_tags.
- Comparison engine is UI-agnostic (no Streamlit imports).

## Acceptance Criteria (Proposed)
- CSV import rejects invalid rows and performs an all-or-nothing insert on valid files.
- Adding a transaction stores amounts as integer cents and normalizes finance fields to lowercase.
- Editing a transaction updates tags through normalized tables with no duplicates.
- Deleting a transaction requires confirmation and removes related tag links.
- CSV import accepts dot-decimal amounts with 0-2 fractional digits; commas and thousands
  separators are invalid; accepts a single date by copying it to the other date field before insert.
- Comparison page supports up to 5 periods and 5 groups, and produces tabular + chart outputs for
  both role and matched-only modes.
- Manage Values can rename/merge payer, payee, category, subcategory, payment_type, and tags; category
  cannot be deleted.
- Backup uses SQLite's online backup API to write a consistent snapshot to the configured directory.
- Database enforces payer/payee invariants with CHECK constraints.
- Export uses a date field selector (default date_application) and includes both date columns.
