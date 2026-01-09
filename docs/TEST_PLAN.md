# Test Plan

## Scope
Validate correctness of the Streamlit + SQLite finance MVP per `PRD.md`, using only synthetic data.
No tests may read from `./data/` or any real user databases/CSVs.

## Test Data Rules
- Use synthetic fixtures only: `tests/fixtures/` or `./.tmp_test/`.
- Use file-backed DBs under `./.tmp_test/` for WAL/backup tests.
- Use `:memory:` only for pure logic tests (parsing, predicates).

## Smoke Tests (Manual)

### App Boot + Settings
- Open app with a new DB path under `./.tmp_test/`; confirm DB is created.
- Verify the app does not override the Streamlit theme setting (light/dark/system).
- Set import/export/backup dirs in settings and confirm persistence across reload.
- Switch DBs; confirm session filters reset and a confirmation appears.

### Transactions
- Add a transaction with only one date; confirm the other date auto-copies.
- Add tags and confirm they display as a sorted, comma-separated list in the table.
- Verify date range filter uses `date_application`.
- Toggle column visibility and sort via column headers; confirm sorting updates the view and all
  filtered transactions remain visible in the scrollable table.
- Delete a transaction with confirmation.

### Import / Export / Backup
- Import a valid semicolon CSV with mixed header casing; confirm rows inserted.
- Import a CSV with an invalid row; confirm no partial insert.
- Import a CSV with comma in tag name; confirm rejection.
- Export with date range + date field selector; confirm both date columns + tags present.
- Export with tag filter; confirm ANY semantics and untagged exclusion.
- Run backup; confirm backup file is created via sqlite backup API.

### Manage Values
- Rename a payer to an existing payer; confirm merge behavior.
- Attempt rename that causes payer == payee; confirm preflight block with conflict count.
- Attempt delete payer when payee is NULL in affected rows; confirm block.
- Attempt delete category; confirm disallowed.
- Rename tag with comma; confirm validation block.

### Compare
- Configure 2 periods, 2 groups; validate output tables per period and node.
- Role vs matched-only outputs differ as expected.
- TagMatch ANY/ALL behavior in category slices + tag filter mode.
- Mixed slices include totals for All Categories/All Tags.
- Charts show one mini bar chart per node (periods on x-axis) laid out horizontally per group;
  each chart uses its own y-scale.
- Toggle "Full year" for a period; confirm start/end snap to Jan 1/Dec 31 of the chosen year.

## Automated Unit/Integration Tests (Synthetic)

### Parsing and Normalization
- Amount parsing:
  - Accept `10`, `10.5`, `10.50`
  - Reject `10,5`, `1,000.00`, `+10`, `-10`, `10.123`
- Normalization:
  - Finance fields lower(trim) enforced; empty/whitespace -> NULL for nullable fields
  - Notes preserve case; whitespace-only invalid if not NULL
- Tag names:
  - Reject commas
  - Enforce lower(trim) and non-empty

### Dates
- Validate ISO shape and calendar validity:
  - Accept `2024-02-29`
  - Reject `2024-02-30`, `2024-13-01`, `2024-00-10`
- Auto-copy: if one of date_payment/date_application is provided, the other is set before insert.
- CSV/app validation should reject invalid calendar dates before DB insert (user-friendly error).

### CSV Import
- Header normalization: trimmed, case-insensitive; duplicates after normalization rejected.
- Required column enforcement: missing `amount`, `category`, or both dates/payer-payee fails.
- Tag parsing: split by comma, trim/lowercase/dedupe, reject commas in tag names.
- Atomicity: any invalid row aborts the entire import.

### CSV Export
- Date field selector default: `date_application`.
- Export includes both dates and tags.
- Tag filter uses ANY semantics; untagged excluded when tags selected.

### DB Constraints
- CHECK constraints for normalized finance fields.
- CHECK constraints for amount >= 0.
- CHECK constraints for payer/payee invariants.
- Tag name constraints (non-empty, lower(trim), comma-free).
- Direct DB insert of non-normalized category (e.g., `" Food "`) should fail.
- App insert of `" Food "` should succeed after normalization.

### PRAGMA
- `PRAGMA foreign_keys` returns `1` after connection.
- File-backed DB uses `journal_mode=wal` (skip WAL assertion for `:memory:` DBs).

### Manage Values
- Preflight blocks:
  - payer == payee conflicts
  - both NULL conflicts on payer/payee deletes
- Rename target validation (non-empty after trim; tags comma-free).

### Comparison Engine
- Role vs matched-only semantics.
- Overlapping A/B sets.
- TagMatch ANY/ALL.
- AND vs OR slice modes.
- All categories/tags nodes behave as totals.
- `#tx (inflow ∪ outflow)` semantics in role mode.
- Use a canonical fixture (8-10 transactions) that includes unmatched inflow, unmatched outflow,
  matched flow, overlapping A/B sets, tagged vs untagged, TagMatch ANY vs ALL differences, and
  at least 2 nodes (one category slice, one tag node, plus All Categories).
  Assert tx_count, inflow, outflow, net, matched_flow explicitly.

### Backup
- Use sqlite backup API to write a snapshot to `./.tmp_test/`.
- Validate backup file exists and opens.
- Backup contains the same row counts as source at time of snapshot.

## Reporting
- Fail fast with clear error messages for constraint violations.
- Avoid printing any real data; use synthetic examples only.

## Last Run
- Command: `python3 -m unittest discover -s tests`
- Result: `Ran 23 tests in 0.096s - OK`
