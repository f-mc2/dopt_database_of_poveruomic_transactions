# Tech Design

## Overview
This document defines the technical design for the Streamlit + SQLite finance app.
It follows PRODUCT_BRIEF.md, UI_BLUEPRINT.md, and DATA_DICTIONARY.md and avoids new features.

## Architecture
- Streamlit multipage app with a thin UI layer and a shared data layer in `src/`.
- `app.py` loads settings, resolves the active finance DB path, and initializes session state.
- `src/` modules:
  - `db.py`: open connections, apply PRAGMA, initialize schema, backup, settings DB helpers.
  - `schema.sql`: authoritative schema for finance DB.
  - `types.py`: dataclasses and enums for Period, Group, Node, modes.
  - `amounts.py`: parse/format amount strings to/from cents.
  - `csv_io.py`: CSV import/export logic and validation.
  - `queries.py`: SQL query builders and WHERE utilities.
  - `tags.py`: tag upsert, tag assignment, and tag queries.
  - `comparison_engine.py`: compute comparison results; no Streamlit imports.
  - `plotting.py`: Altair charts for comparison outputs.
  - `ui_widgets.py`: P1/P2/P3 widget helpers.

## Databases

### Finance DB (finance.db)
SQLite database with WAL and foreign keys enabled for each connection:
- `PRAGMA journal_mode=WAL;`
- `PRAGMA foreign_keys=ON;`

Schema (logical):
- `transactions`:
  - id INTEGER PRIMARY KEY
  - date_payment TEXT NOT NULL
  - date_application TEXT NOT NULL
  - amount_cents INTEGER NOT NULL
  - payer TEXT NULL
  - payee TEXT NULL
  - category TEXT NOT NULL
  - subcategory TEXT NULL
  - payment_type TEXT NULL
  - notes TEXT NULL
  - CHECK (length(trim(category)) > 0 AND category = lower(trim(category)))
  - CHECK (payer IS NULL OR (length(trim(payer)) > 0 AND payer = lower(trim(payer))))
  - CHECK (payee IS NULL OR (length(trim(payee)) > 0 AND payee = lower(trim(payee))))
  - CHECK (subcategory IS NULL OR (length(trim(subcategory)) > 0 AND subcategory = lower(trim(subcategory))))
  - CHECK (payment_type IS NULL OR (length(trim(payment_type)) > 0 AND payment_type = lower(trim(payment_type))))
  - CHECK (notes IS NULL OR length(trim(notes)) > 0)
  - CHECK (amount_cents >= 0)
  - CHECK (date_payment GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]' AND
      date(date_payment) IS NOT NULL AND date(date_payment) = date_payment)
  - CHECK (date_application GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]' AND
      date(date_application) IS NOT NULL AND date(date_application) = date_application)
  - CHECK (payer IS NOT NULL OR payee IS NOT NULL)
  - CHECK (payer IS NULL OR payee IS NULL OR payer <> payee)
- `tags`:
  - id INTEGER PRIMARY KEY
  - name TEXT NOT NULL UNIQUE
    CHECK (length(trim(name)) > 0 AND instr(name, ',') = 0 AND name = lower(trim(name)))
- `transaction_tags`:
  - transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE
  - tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE
  - PRIMARY KEY (transaction_id, tag_id)

Indexes (recommended):
- `transactions(date_payment)`, `transactions(date_application)`
- `transactions(category)`, `transactions(subcategory)`
- `transactions(payer)`, `transactions(payee)`, `transactions(payment_type)`
- `transaction_tags(transaction_id)`, `transaction_tags(tag_id)`
- `tags(name)` (UNIQUE implies index in SQLite)

Subcategory is hierarchical at the application level: the semantic key is (category, subcategory).

### App Settings DB (app_settings.db)
Stored at `/data/app_settings.db` (inside the data volume).

Schema (logical):
- `app_settings` (single row enforced by CHECK):
  - id INTEGER PRIMARY KEY CHECK (id = 1)
  - last_used_db_path TEXT NULL
  - theme TEXT NOT NULL CHECK (theme IN ('light','dark'))
  - csv_import_dir TEXT NULL
  - csv_export_dir TEXT NULL
  - db_backup_dir TEXT NULL
- `recent_db_paths`:
  - path TEXT PRIMARY KEY
  - last_used_at INTEGER NOT NULL

Settings rules:
- Paths are stored verbatim (case-preserving).
- Recent DBs list is capped at 3 by `last_used_at`.
- Environment defaults are used when the stored setting is NULL.

## Validation and Normalization
- Finance-domain text fields are trimmed and lowercased:
  payer, payee, category, subcategory, payment_type, tag names.
- Notes are trimmed but preserve case.
- Tag names cannot contain commas (to keep CSV round-trip safe).
- Empty strings become NULL for nullable fields.
- DB enforces lowercase normalization and non-empty values for finance-domain fields
  (nullable fields must be NULL or non-empty after trim).
- Dates must be YYYY-MM-DD; DB enforces ISO shape and non-null parseability via CHECK,
  and the app enforces calendar validity.
- Full calendar validity is enforced in application code via `datetime.date.fromisoformat()`.
- If only one of `date_payment` or `date_application` is provided (UI/CSV), copy it to the other
  before insert.
- Payer/payee invariants (not both NULL, not equal) are validated in code and enforced in DB.
- Manage Values delete preflight:
  - Deleting payer X is blocked if any transaction with payer X has payee NULL.
  - Deleting payee Y is blocked if any transaction with payee Y has payer NULL.
- Manage Values rename/merge preflight:
  - Block operations that would make payer == payee; show counts of conflicting rows.
- Rename targets are validated (non-empty after trim; tags cannot contain commas).
- Amounts:
  - Dot decimal only; commas and thousands separators are invalid.
  - Allow digits with optional decimal part of 0-2 digits.
  - Reject inputs with more than two decimals before quantize.
  - Convert with Decimal, quantize to 2 decimals (padding only), and multiply by 100 to `amount_cents`.
  - Reject signed amounts (no leading + or -).

## CSV Import
- Semicolon-separated CSV.
- Required columns:
  - `amount`
  - `category`
  - at least one of `date_payment` / `date_application`
  - at least one of `payer` / `payee`
- Optional columns: `payer`, `payee`, `subcategory`, `payment_type`, `notes`, `tags`.
- `tags` column is comma-separated; trim, lowercase, dedupe, drop empties.
- No escaping is supported; tag names cannot contain commas.
- Validation occurs for all rows first; insert runs inside a single transaction.
- If any row is invalid, the import aborts without partial inserts.
- Validate dates with `datetime.date.fromisoformat()` before insert.

## CSV Export
- Date field selector: `date_payment` or `date_application` (default `date_application`).
- Required date range filter based on selected date field.
- Optional filters: payer, payee, category, subcategory, payment_type, tags.
- If tags are selected, untagged transactions are excluded.
- Multiple selected tags use ANY semantics (match any selected tag).
- Export includes both date columns and a `tags` column (comma-separated).
- Amounts are formatted with a dot decimal and two digits.

## Comparison Engine

### Inputs
- Periods: up to 5, each with label, start_date, end_date (inclusive), or full range.
- Groups: up to 5, each with label and two sets:
  - A (payers)
  - B (payees)
- Date field: `date_payment` or `date_application`.
- Mode: `role` or `matched_only`.
- Node selection:
  - AND mode: category/subcategory nodes + tag list with TagMatch ANY/ALL.
  - OR mode: nodes can be category, subcategory, tag, all_categories, all_tags.
  - Selected nodes are evaluated independently; outputs are per node.

### Node Predicates
- Category node: `tx.category == category`.
- Subcategory node: `tx.category == category AND tx.subcategory == subcategory`.
- Tag node: `tx` has tag.
- All categories node: matches all transactions (no category filter).
- All tags node: matches all transactions (no tag filter).

### TagMatch (AND mode)
- ANY: transaction has at least one of the selected tags.
- ALL: transaction has all selected tags.
- If tag list is empty, TagMatch is true.
- If tag list is non-empty, transactions with no tags fail TagMatch.

### Mode Semantics
For each period P, group G=(A,B), and node N:
- Role mode:
  - Outflow: sum `amount_cents` where payer in A and node predicate matches.
  - Inflow: sum `amount_cents` where payee in B and node predicate matches.
  - Net: inflow - outflow.
  - tx_count: count of distinct transactions that match node predicate and have
    payer in A or payee in B.
- Matched-only mode:
  - Matched flow: sum `amount_cents` where payer in A and payee in B and node matches.
  - tx_count: count of distinct matched transactions.

### Output Shape
Comparison engine returns a dataframe with:
- period_label
- group_label
- node_label (friendly labels for all_categories/all_tags)
- tx_count
- inflow_cents
- outflow_cents
- net_cents
- matched_flow_cents
- mode

UI rendering:
- Tables are per period and node: rows are groups.
- Role mode shows #tx (inflow ∪ outflow), inflow, outflow, net.
- Matched-only mode shows #transactions and matched flow.

## Query Strategy
- All SQL uses `?` placeholders only.
- Base transaction filters are built from date range and node predicate.
- Tag filters:
  - ANY uses `EXISTS` on `transaction_tags` with `IN` list.
  - ALL uses `GROUP BY transaction_id HAVING COUNT(DISTINCT tag_id) = ?`.
- Transactions and export filters use ANY semantics.
- Role mode inflow/outflow can be computed with conditional sums in one query or as two queries,
  but results must be consistent with the tx_count definition.

## Backup
- Use `sqlite3.Connection.backup()` to create a consistent snapshot under WAL mode.
- Backup file name includes a timestamp and is stored in `db_backup_dir`.

## Tests (Synthetic Only)
- Use file-backed DBs under `./.tmp_test/` for WAL and backup tests.
- Use `:memory:` only for pure logic tests (no WAL/backup).
- Never touch `./data/`.
- Suggested tests:
  - Schema invariants: payer/payee CHECK constraints and tag cascade deletes.
  - Amount parsing: valid dot-decimal; reject commas and >2 decimals.
  - Date validation: invalid calendar dates are rejected before insert.
  - Date auto-copy: one date provided populates the other.
  - CSV import/export round-trip with tags.
  - Export date field selector and default behavior.
  - Comparison engine: role vs matched-only, overlapping A/B sets,
    AND vs OR node logic, TagMatch ANY/ALL, all_categories/all_tags nodes.
  - Backup path uses sqlite backup API.
