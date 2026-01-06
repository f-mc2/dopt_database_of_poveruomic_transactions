# DOPT (Database of Poveruomic Transactions) - Personal Finance Dashboard (Streamlit + SQLite) — MVP PRD


## 0) One-line summary
A single-user, local-first Streamlit app to manage a SQLite transaction database with CSV import/export, per-transaction edit/delete, value management (rename/delete), manual timestamped backups, and a comparison engine (periods × groups × nodes) with grouped-bar plots. No saved presets.

---

## 1) Goals (MVP)
1. Create/open a SQLite database at a **custom user-specified file path**.
2. Import transactions from semicolon-separated CSV with validation + preview.
3. Export transactions to CSV with filters (including reconstructed tags column).
4. Edit/delete **single transactions** (no bulk edit).
5. Manage field values:
   - rename/delete values for `payer`, `payee`, `category`, `subcategory`
   - rename/delete tags (normalized tags table)
6. Manual database backup on user request to a **custom directory**, filename includes **date+time** timestamp.
7. Comparison page:
   - user defines **1–5 periods** (labeled date ranges)
   - user defines **1–5 groups** (labeled payer/payee sets)
   - user defines nodes (AND/OR selection modes)
   - compute aggregates per (period × group × node-member)
   - plot grouped bars with stable period colors
8. All selection UIs should default to **existing DB values**; allow adding new values where appropriate.

---

## 2) Non-goals (out of MVP)
- Authentication, multi-user support, cloud sync, bank connections, OCR, AI categorization.
- Budgeting, recurring transactions, scheduled backups, automatic syncing.
- Persistent/saved presets for dashboards/filters/comparisons.

---

## 3) Target environment
- Single user running locally or via Docker.
- Later deployment via Docker Compose with bind-mounted volumes for DB/exports/backups.
- No credentials stored.

### 3.1 Configuration (env defaults + UI override)
Environment defaults:
- `FINANCE_DB_PATH` default `/data/finance.db`
- `FINANCE_EXPORT_DIR` default `/data/exports`
- `FINANCE_BACKUP_DIR` default `/data/backups`

UI allows overriding per session (stored in `st.session_state`).

---

## 4) Database model and storage

### 4.1 SQLite configuration
- Enable WAL mode: `PRAGMA journal_mode=WAL;`
- Enforce foreign keys: `PRAGMA foreign_keys=ON;`
- All SQL uses parameter placeholders only (`?`), never string formatting.

### 4.2 Schema (authoritative)

#### `transactions`
Fields:
- `id` INTEGER PRIMARY KEY
- `date_payment` TEXT NOT NULL (ISO `YYYY-MM-DD`)
- `date_application` TEXT NOT NULL (ISO `YYYY-MM-DD`)
- `amount_cents` INTEGER NOT NULL (currency magnitude)
- `payer` TEXT NULL
- `payee` TEXT NULL
- `category` TEXT NOT NULL (stored lowercase)
- `subcategory` TEXT NULL (stored lowercase)
- `notes` TEXT NULL
- `created_at` TEXT NOT NULL (ISO timestamp)
- `updated_at` TEXT NOT NULL (ISO timestamp)

Constraints:
- `CHECK (amount_cents >= 0)`
- `CHECK (payer IS NULL OR payee IS NULL OR payer <> payee)`

Indexes (minimum):
- index on `date`
- index on `(category, subcategory)`
- index on `payer`
- index on `payee`

#### `tags`
- `id` INTEGER PRIMARY KEY
- `name` TEXT NOT NULL UNIQUE (stored lowercase)

#### `transaction_tags`
- `transaction_id` INTEGER NOT NULL REFERENCES `transactions(id) ON DELETE CASCADE`
- `tag_id` INTEGER NOT NULL REFERENCES `tags(id) ON DELETE CASCADE`
- PRIMARY KEY (`transaction_id`, `tag_id`)

> Tags are **normalized**. There is no `transactions.tags` column in the DB.

### 4.3 Amount conversion (CSV → DB)
CSV provides an `amount` field (string/float). DB stores `amount_cents`:
- parse with decimal safety (e.g. Python `Decimal`)
- allow comma decimal in CSV (convert to dot before parsing)
- convert to integer cents by rounding to 2 decimals
- store nonnegative magnitude (reject negative amounts in MVP)

---

## 5) CSV import/export

### 5.1 CSV import (semicolon-separated)
Flow:
1. User uploads CSV (semicolon-separated).
2. App previews first N rows and shows detected columns.
3. App validates; if any invalid rows exist, show an error report with row numbers and reasons; **do not import anything**.
4. User confirms import.
5. App inserts rows into DB within a single SQL transaction.

Required columns:
- `date` (strict `YYYY-MM-DD`)
- `amount`
- `category` (stored lowercase)

Optional columns:
- `payer`, `payee`, `subcategory`, `notes`
- `tags` (comma-separated string, e.g. `rent,home`)

Rules:
- Trim whitespace everywhere.
- Empty strings become NULL.
- Normalize to lowercase: `category`, `subcategory`, tags.
- Enforce `payer != payee` when both are present.
- Tags import:
  - split by comma `,`
  - trim + lowercase
  - drop empty entries
  - deduplicate
  - upsert tags into `tags`, then link via `transaction_tags`.

### 5.2 CSV export
User chooses:
- date range (required)
- optional filters: payer(s), payee(s), category(s), subcategory(s), tag(s)

Export behavior:
- Export columns aligned with import schema, including a `tags` column.
- `tags` is reconstructed from `tags`/`transaction_tags` as a comma-separated list.
- Provide:
  - Streamlit download button
  - optionally save file into `FINANCE_EXPORT_DIR` (if configured)

---

## 6) Transactions (single-row edit/delete)

### 6.1 List + filter
Transactions page supports:
- date range filter
- payer(s), payee(s), category(s), subcategory(s), tag(s) filters
- free-text search over payer/payee/category/subcategory/notes (and optionally tags)

Display:
- Table showing `id`, date, amount, payer, payee, category, subcategory, tags, notes.
- Each row supports:
  - Edit action
  - Delete action (with confirmation)

### 6.2 Edit form (single transaction)
Editable fields:
- date, amount, payer, payee, category, subcategory, tags, notes

Selection UI:
- payer/payee/category/subcategory: choose from existing distinct values; include “(empty)” and an “Add new…” path.
- tags: multiselect from existing tags; allow adding a new tag.

### 6.3 Delete
- Confirm deletion.
- Cascade removes tag links due to FK constraints.

---

## 7) Manage Values (rename/delete)

### 7.1 Rename/delete payer/payee/category/subcategory
For each field:
- list distinct values + usage counts
- rename:
  - update all matching transactions to new value
  - reject empty rename target
- delete:
  - set field to NULL for all matching transactions
  - require confirmation and show affected row count

### 7.2 Manage tags
- list tags + usage counts
- rename tag:
  - update `tags.name`
  - refuse collisions (unique constraint)
- delete tag:
  - delete from `tags`
  - cascade removes links in `transaction_tags`

---

## 8) Database open/create + settings

### 8.1 Custom DB location
Home page:
- user inputs DB file path
  - if exists: open and validate schema
  - if not: offer to create schema
- if parent directory does not exist: show error
- store DB path in session state
- allow “Switch DB” action

### 8.2 Theme setting (optional)
If implemented, provide a simple UI toggle for light/dark appearance where feasible within Streamlit constraints.

---

## 9) Backup (manual, timestamped)
Backup page:
- button “Backup now”
- uses SQLite backup API: `sqlite3.Connection.backup()`
- output filename: `finance_backup_YYYYMMDD_HHMMSS.db` (system local time)
- backup directory configurable (`FINANCE_BACKUP_DIR`)
- ensure directory exists or create it

---

## 10) Comparison logic (Period × Group × Node × Mode)

### 10.1 Purpose
Compute and visualize aggregates across:
- multiple labeled date periods
- multiple labeled payer/payee groups
- multiple node-members (categories/subcategories/tags depending on selection mode)

Return a simple, render-ready structure (dataframe/dict) and grouped-bar plots.

### 10.2 Inputs

#### 10.2.1 Periods (1–5)
Each period:
- `label`
- `start_date` (YYYY-MM-DD)
- `end_date` (YYYY-MM-DD), inclusive

#### 10.2.2 Groups (1–5)
Each group \(G_i\):
- `label`
- payer set \(A_i\) (list of payers)
- payee set \(B_i\) (list of payees)

Selection UI:
- typeahead (text input + filtered selectbox) from distinct DB values.

#### 10.2.3 Computation mode
- `role` (default)
- `matched_only`

#### 10.2.4 Node selection mode
User chooses one:

**A) OR mode (independent nodes)**
- select up to 10 nodes; each node is one of:
  - category `Category`
  - subcategory `Category:Subcategory`
  - tag `tag`
- each selected node is a node-member (x-axis category)

**B) AND mode (category/subcategory entries + tags)**
- select up to 10 category/subcategory entries from a unified dropdown list:
  - category shown as `Category`
  - subcategory shown as `Category:Subcategory`
- select any number of tags
- user selects TagMatch:
  - `ANY` (default) or `ALL`

In AND mode, node-members are:
- if at least one category/subcategory entry selected:
  - node-members are those selected entries
  - member predicate = (entry predicate) AND (tag predicate if tags selected)
- else (no category/subcategory entry selected):
  - node-members are the selected tags
  - member predicate = “has this tag”
  - TagMatch is ignored in this branch because tags are the members.

### 10.3 Node predicates

Category `C`:
- `transactions.category = C`

Subcategory `C:SC`:
- `transactions.category = C AND transactions.subcategory = SC`

Tag `t`:
```sql
EXISTS (
  SELECT 1
  FROM transaction_tags tt
  JOIN tags tg ON tg.id = tt.tag_id
  WHERE tt.transaction_id = transactions.id
    AND tg.name = ?
)
```

TagMatch in AND mode (when tags are a filter, not members):

* ANY: one EXISTS with `tg.name IN (?, ?, ...)`
* ALL: AND of EXISTS for each selected tag

### 10.4 Bucket logic per group

Let (A_i) be the payer set, (B_i) the payee set.

NULL handling:

* `payer ∉ A_i` interpreted as `(payer IS NULL OR payer NOT IN A_i)`
* `payee ∉ B_i` interpreted as `(payee IS NULL OR payee NOT IN B_i)`

Use `amount_cents` (already nonnegative magnitude).

**Mode = role**

* outflow: payer ∈ A_i AND payee ∉ B_i
* inflow: payee ∈ B_i AND payer ∉ A_i
* internal: payer ∈ A_i AND payee ∈ B_i
* net = inflow − outflow

**Mode = matched_only**

* internal: payer ∈ A_i AND payee ∈ B_i
* inflow = outflow = net = 0

### 10.5 Outputs

For each `(period × group × node-member)` compute:

* `tx_count = COUNT(*)`
* `inflow_cents = SUM(amount_cents)` over inflow predicate
* `outflow_cents = SUM(amount_cents)` over outflow predicate
* `internal_cents = SUM(amount_cents)` over internal predicate
* `net_cents = inflow_cents - outflow_cents`

Return as:

* long dataframe with columns:

  * `period, group, node, tx_count, inflow_cents, outflow_cents, internal_cents, net_cents`
    or an equivalent dict keyed by `(period_label, group_label, node_label)`.

The computation module must be UI-agnostic (no Streamlit imports).

### 10.6 Plots

For each group (separately), render a grouped bar chart:

* x-axis: node-members
* within each node-member: one bar per period (clustered side-by-side)
* different colors per period
* stable period→color mapping based on period order
* visible spacing between node clusters

Minimum chart: `net_cents`. Optional toggles: inflow/outflow/internal.

Preferred implementation: Altair grouped bars using `xOffset=period`.

### 10.7 Limits

* max periods: 5
* max groups: 5
* OR mode: max nodes: 10
* AND mode: max category/subcategory entries: 10; tags unlimited (warn if TagMatch=ALL with many tags)

Performance (MVP): iterate periods × groups × members, run 1 aggregation query per cell.

---

## 11) Pages (Streamlit multipage)

1. Home / Open DB / Settings
2. Transactions (list + edit + delete)
3. Import / Export
4. Manage Values (rename/delete fields; manage tags)
5. Compare (periods/groups/nodes + plots)
6. Backup

---

## 12) Acceptance criteria (MVP “done”)

* User can create/open DB at arbitrary path; schema created automatically.
* CSV import previews + validates; aborts on errors; inserts atomically; tags normalized into join tables.
* CSV export supports filters and includes `tags` column reconstructed from join tables.
* User can edit/delete a single transaction; selectors use DB values by default.
* User can rename/delete payer/payee/category/subcategory values with counts + confirmations.
* User can rename/delete tags safely (unique constraint, cascade links).
* Backup creates timestamped DB copy using SQLite backup API.
* Comparison:

  * supports 1–5 periods, 1–5 groups
  * supports role and matched_only
  * supports AND/OR node selection modes with TagMatch ANY/ALL in AND mode
  * outputs correct dataframe and grouped-bar plots with stable period colors.
* Code is modular and Docker-compose-ready (paths via env variables + bind mounts).

---

## 13) Out-of-scope backlog (future)

* Presets/saved dashboards
* Scheduled backups + retention policies
* Bulk edit
* Advanced analytics (rolling averages, forecasting)
* Multi-currency support


