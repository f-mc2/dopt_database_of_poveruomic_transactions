# PRD - Streamlit + SQLite Finance Dashboard (MVP)

## Status
- Phase: Approved (implementation changes allowed)
- Source docs: `PRODUCT_BRIEF.md`, `UI_BLUEPRINT.md`, `DATA_DICTIONARY.md`, `TECH_DESIGN.md`

## Summary
Build a single-user, local Streamlit finance dashboard backed by SQLite. Core outcomes:
CSV import/export, transaction CRUD, comparison analytics, value management, and reliable backups.
The app runs on a desktop host and is usable on mobile browsers.

## Goals
1. Strict, atomic CSV import/export for transactions (semicolon-separated).
2. One-at-a-time transaction add/edit/delete with normalized tags.
3. Comparison analytics with periods, groups, and node slices.
4. Bulk rename/merge of reference values (payer, payee, category, subcategory, payment_type, tags).
5. WAL-safe database backup.

## Non-goals
- Multi-user support, cloud sync, budgets, forecasting, recurring transactions.
- Bulk edit/delete of transactions (except controlled Manage Values operations).
- Multi-currency.

## Personas and Context
- One user, local deployment (Docker optional), primarily desktop usage with mobile access.
- Data stored locally under `./data/` (host) or `/data` (container).

## UX Principles
- Follow widget patterns in `UI_BLUEPRINT.md` (P1/P2/P3).
- Prefer existing values; creation allowed only in explicit contexts.
- Confirm destructive operations.
- Keep UI deterministic and consistent with DB constraints.
- Nullable P1 fields expose an explicit "(none)" choice to store NULL.

## Functional Requirements

### Home
- H1: Allow selecting a finance DB path from env default, recent list (max 3), or manual input.
- H2: Allow creating a new empty DB if the path does not exist (default under data dir).
- H3: Persist last-used DB and recent list in settings DB; load on startup.
- H4: Switching DB resets session filters/state and shows confirmation.
- H5: Sidebar label for the main page is "HOME"; the top header is "Home" with a matching anchor.
- H6: Theme is controlled by Streamlit settings (light/dark/system); no in-app theme selector.
- H7: Editable config for import/export/backup directories, persisted in settings DB.

### Tutorial
- TU1: Dedicated tutorial page in the sidebar (label "Tutorial").
- TU2: README-style tutorial section with comparison logic explainer; content finalized later.

### Transactions
- T1: Filters include date range, payer, payee, category, subcategory, payment_type, tags.
- T2: Date range filter applies to `date_application` (no selector in MVP).
- T3: Missing-value toggles for payer/payee/payment_type.
- T4: Subcategory options are filtered by selected category.
- T5: Tag filters use ANY semantics; if tags selected, untagged tx are excluded.
- T6: List view is a scrollable table showing all filtered transactions with all fields as columns;
  tags shown as a comma-separated, lexicographically sorted list.
- T6a: Default column order is id, date_payment, date_application, payer, payee, amount_cents,
  category, subcategory, notes, tags, payment_type.
- T6b: Column display labels are id, Date payment, Date application, Payer, Payee, Amount
  (amount_cents/100), Category, Subcategory, Notes, Tags, Payment type.
- T7: User can hide/show columns.
- T8: Default order is date_application desc, id desc; user can sort by clicking column headers
  in the table (no separate sort control or pagination in MVP).
- T9: Add/edit forms support all fields and tag assignment.
- T10: If only one date is provided, auto-copy to the other before save.
- T11: Delete requires confirmation.
- T12: A free-text search input appears above the table; it filters by matching payer, payee,
  category, subcategory, tags, or notes (combined with other filters).
- T13: Filter controls (date range, payer, payee, category, subcategory, payment_type, tags,
  missing-value toggles) render below the table.

### Import/Export/Backup
- IE1: Import semicolon-separated CSV with strict validation and atomic insert.
- IE2: Required columns: `amount`, `category`, at least one of `date_payment`/`date_application`,
  and at least one of `payer`/`payee`.
- IE2a: CSV headers are trimmed and case-insensitive; duplicates after normalization are invalid.
- IE3: Amount format: dot decimal only; 0-2 fractional digits; no commas or thousands separators;
  no sign; reject >2 decimals.
- IE4: Tags column is comma-separated; no escaping; tag names cannot contain commas.
- IE5: If only one date provided in a row, copy it to the other before insert.
- IE6: Export requires date range and date-field selector (default `date_application`).
- IE7: Export filters use P2/P3b; tag filter uses ANY semantics.
- IE8: Export includes both date columns and a `tags` column.
- IE9: Backup uses SQLite online backup API; confirmation required.

### Manage Values
- MV1: Entities: payer, payee, category, subcategory, payment_type, tags.
- MV2: Rename/merge is allowed; if target exists, merge.
- MV3: Deletions:
  - Tags/subcategories can be removed.
  - Payer/payee/payment_type delete sets NULL.
  - Category cannot be deleted.
- MV4: Preflight blocks operations that would violate payer/payee invariants:
  - payer == payee conflicts
  - both NULL conflicts when deleting payer/payee
- MV5: Rename targets validated (non-empty after trim; tags forbid commas).
- MV6: Renames/merges require confirmation.

### Compare
- C1: Periods: up to 5; each with label and start/end (inclusive) or full range.
- C1a: Each period can toggle "Full year" to select a single year (Jan 1–Dec 31).
- C2: Groups: up to 5; each group has payer set A and payee set B.
- C3: Date field selector applies to all periods.
- C4: Modes: role vs matched-only (perfect-match label OK).
- C5: Slice modes:
  - Category slices + tag filter (AND mode): up to 10 category/subcategory nodes plus tag list.
  - Mixed slices (OR mode): up to 10 nodes across category/subcategory/tags plus totals.
- C6: "All categories" and "All tags" are total slices; nodes are evaluated independently.
- C6a: OR-mode node labels are disambiguated (e.g., `category:food`, `tag:food`) to avoid collisions.
- C7: TagMatch ANY/ALL applies only in category slices + tag filter mode.
- C8: Output tables per period + node; rows are groups; columns:
  - Role mode: `#tx (inflow ∪ outflow)`, inflow, outflow, net.
  - Matched-only: `#transactions`, matched flow.
- C9: Charts are per group; nodes are displayed horizontally as separate mini bar charts
  (periods on x-axis) with independent y-scales.

## Data Model and Validation
Authoritative definitions are in `DATA_DICTIONARY.md`. Key rules:
- amount stored as `amount_cents INTEGER NOT NULL`, non-negative.
- Finance-domain fields must already be normalized (lower(trim())); DB rejects non-normalized values
  via CHECK constraints.
- Notes preserve case; empty/whitespace-only values are invalid if not NULL.
- Tag names are normalized, non-empty, and cannot contain commas (DB CHECK).
- Payer/payee cannot both be NULL and cannot be equal (DB CHECK).
- Dates must be ISO shape; DB rejects dates not parseable by SQLite `date()`, and the app validates
  with `datetime.date.fromisoformat()` for user-friendly errors.
- All SQL uses parameter placeholders (`?`).
- All write paths normalize input and convert empty/whitespace-only values to NULL before insert/update.

## Comparison Semantics (Summary)
For each period P, group G=(A,B), node N:
- Role mode:
  - Outflow: sum amount where payer in A and node matches.
  - Inflow: sum amount where payee in B and node matches.
  - Net = inflow - outflow.
  - `#tx (inflow ∪ outflow)` = distinct tx where payer in A OR payee in B and node matches.
- Matched-only:
  - Matched flow: sum amount where payer in A AND payee in B and node matches.
  - `#transactions` = distinct matched tx.

## Settings and Persistence
- Settings DB: `app_settings.db` stored alongside the active finance DB (parent of DOPT_DB_PATH).
  Host default is `./data/app_settings.db`; container default is `/data/app_settings.db` when
  running in Docker. If DOPT_DB_PATH points elsewhere, the settings DB follows it. Stores
  last-used DB, recent DBs (max 3), and import/export/backup dirs.
- Settings DB is the only persisted UI config; no saved reports/presets.

## Non-functional Requirements
- Streamlit multipage UI.
- SQLite via sqlite3; WAL + foreign keys enabled per connection.
- All operations respect repo/data safety rules in `../AGENTS.md`.

## Acceptance Criteria
- Import rejects invalid rows and inserts atomically.
- Amount parsing accepts dot-decimal with 0-2 digits; rejects comma/thousands/signs.
- Dates accept one provided date and copy to the other; invalid calendar dates are rejected in app.
- Tag names cannot contain commas (UI + DB enforced).
- Payer/payee invariants are enforced by DB and preflight UI.
- Transactions list supports column hide/show, table sorting, and shows all filtered transactions;
  date filter uses `date_application`.
- Comparison outputs match role vs matched-only semantics and node slicing.
- Backup uses SQLite online backup API to create consistent snapshots.

## Risks / Notes
- DB-level normalization requires strict normalization in all writes; app should normalize before insert.
- Enabling strict DB checks assumes new DBs or migrated data; app should fail fast with a clear
  message if existing data violates CHECK constraints.
