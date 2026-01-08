# UI Blueprint

## Global Layout and Rules
- Streamlit multipage navigation in the sidebar.
- Desktop-first layout with mobile-safe stacking.
- Destructive actions always require explicit confirmation.
- No arbitrary bulk edit/delete of transactions; only one-at-a-time edits.
  Controlled bulk operations are limited to Manage Values rename/merge/delete.
- Finance-domain values are stored in lowercase; notes preserve case. Search is case-insensitive.
- Use existing values whenever possible; creation is allowed only in explicit contexts
  (transaction entry, tag assignment, and Manage Values rename/merge).
- Tag names cannot contain commas to ensure CSV round-tripping.
- Missing payer/payee/payment_type are stored as NULL; NULL values are not selectable in filters.
- Payer must always differ from payee; operations that would violate this are blocked with a warning.
- Selected database path and UI theme persist across sessions via a small settings SQLite DB
  stored in the data directory (gitignored); it remembers last-used DB and up to 3 recent DBs.

## Widget Patterns

### P1 Select-or-Create
Single text input with suggestion list. User can pick an existing value or type a new one.
- UI: text_input + filtered suggestions list.
- Behavior: creation happens only on form submit; show a "will create new value" preview if the input
  does not match an existing value.
- Input is normalized (trim + lowercase) before comparison and preview.
- Use for: transaction entry fields (payer, payee, category, subcategory, payment_type) and tag creation.

### P2 Select-Existing-Only
Select existing values only (no creation).
- UI: selectbox or multiselect with built-in search.
- Use for: filters, comparison selectors, manage-values selectors.

### P3a Tags Assign
Assign tags to a transaction with the option to add new tags.
- UI: multiselect of existing tags + text_input to add a new tag.
- Behavior: add input value to tag list if new, then include it in selection.

### P3b Tags Filter
Filter by tags from existing values only.
- UI: multiselect (built-in search).
- No new tag creation.

## Pages

### Home
Purpose: quick orientation and app status.
- Database selection:
  - Default path from environment.
  - Recent DB list (max 3) plus manual path input to override.
  - Allow creating a new empty DB if the path does not exist (default under data dir).
  - Persist selection across sessions and load the chosen database on startup.
  - Switching DBs resets session filters/state and shows a confirmation.
- Theme selector (light/dark), persisted across sessions in the settings DB.
- README-style tutorial section (headers, text, bullets) with a comparison logic explainer;
  optional images; final content defined later.
- Configuration section for import/export/backup directories (editable, persisted in settings DB).

### Transactions
Purpose: view and maintain transactions.
- Filters (P2/P3b): date range, payer, payee, category, subcategory, payment_type, tags.
- Date range filter applies to date_application (no selector in MVP).
- Missing-value toggles: include missing payer, payee, or payment_type.
- Subcategory choices are filtered by the selected category.
- If any tags are selected, untagged transactions are excluded.
- Multiple selected tags use ANY semantics (match any selected tag).
- List view: scrollable table with all filtered transactions and all fields as columns; tags shown
  as a comma-separated, lexicographically sorted list; allow column hide/show; default order is
  date_application desc, id desc; user can sort by clicking column headers in the table; no
  separate sort menu or pagination in MVP.
- Add transaction (form):
  - Fields: date_payment, date_application, amount, payer, payee, category, subcategory,
    payment_type, notes, tags.
  - Use P1 for payer/payee/category/subcategory/payment_type.
  - Use P3a for tags.
  - Subcategory suggestions are scoped to the selected category.
  - If only one date is provided, auto-copy it into the other field before save.
- Edit transaction (one at a time): same fields as add.
- Delete transaction: confirmation required.

### Import/Export
Purpose: CSV import, export, and backup.
- Import:
  - File uploader for semicolon-separated CSV.
  - Validate required columns (amount, category, at least one of date_payment/date_application,
    and at least one of payer/payee).
  - Amount format uses a dot as decimal separator; commas and thousands separators are invalid.
  - Tags column (if present) is comma-separated; no escaping is supported; tag names cannot
    contain commas.
  - Abort on any invalid row; no partial inserts.
  - If only one date is provided in a row, copy it to the other before insert.
- Export:
  - Date field selector: date_payment or date_application.
  - Default date field is date_application.
  - Required date range selection.
  - Optional filters using P2/P3b.
  - Missing-value toggles: include missing payer, payee, or payment_type.
  - Multiple selected tags use ANY semantics (match any selected tag).
  - Download button; optional save to configured export directory.
  - Export includes both date_payment and date_application columns and a tags column.
- Backup:
  - Show configured backup directory.
  - Backup action with confirmation; writes a timestamped copy.

### Manage Values
Purpose: bulk rename/merge and cleanup of reference values.
- Entities: payer, payee, category, subcategory, payment_type, tags.
- For each entity:
  - Select existing value (P2).
  - Rename to new value (free text input). If target exists, treat as merge.
  - Delete behavior:
    - Tags and subcategories can be removed.
    - Payer/payee/payment_type delete sets field to NULL.
    - Category cannot be deleted (rename/merge only).
- Subcategory operations are scoped to category (operate on category + subcategory pairs).
- Any operation that would result in payer == payee is blocked with a warning.
- Deleting payer or payee values is blocked if it would make any transaction have both NULL
  (show count of blocking transactions).
- Renames/merges are blocked if they would make payer == payee (show count of conflicts).
- Rename targets are validated (non-empty after trim; tags cannot contain commas).
- Renames/merges require confirmation because they are destructive.

### Compare
Purpose: comparison engine with periods, groups, and node selection.
- Date field selector: date_payment or date_application (applies to all periods).
- Periods:
  - Up to 5 periods, each with start date and end date (or full range).
  - Default number of periods is 1.
- Groups:
  - Up to 5 groups; default number of groups is 1.
  - Each group Gi has:
    - Ai: selected payers (P2, multiselect).
    - Bi: selected payees (P2, multiselect).
- Mode:
  - Role mode vs matched-only mode (UI label can use "perfect-match" for matched-only).
  - Role mode outputs inflow, outflow, and net (inflow - outflow).
  - Matched-only mode outputs a single matched flow (payer in A and payee in B).
- Node selection (categories/subcategories and tags):
  - Slice mode:
    - Category slices + tag filter (AND mode):
      - Select up to 10 category/subcategory nodes (P2) with an "All categories" option.
      - Select tags (P3b). Tag match uses ANY or ALL.
    - Mixed slices (OR mode):
      - Select up to 10 nodes across category/subcategory/tags (P2) with "All categories" and
        "All tags" options.
  - Subcategory nodes are category-scoped (category + subcategory pairs).
  - "All categories" and "All tags" are total slices (no category or tag filter).
  - Selected nodes are evaluated independently; UI produces one output block per node.
  - TagMatch ANY/ALL applies only in category slices + tag filter mode.
- Output:
  - Results table and grouped bar charts.
  - Tables are per period and node: rows are groups; columns are #tx (inflow ∪ outflow), inflow,
    outflow, and net in role mode, or #transactions and matched flow in matched-only mode.
