# UI Blueprint

## Global Layout and Rules
- Streamlit multipage navigation in the sidebar.
- Desktop-first layout with mobile-safe stacking.
- Each page sets Streamlit layout to wide via set_page_config.
- Destructive actions always require explicit confirmation.
- No arbitrary bulk delete of transactions; only one-at-a-time deletes.
  Transactions-plus allows bulk edits with explicit save; controlled bulk operations
  are otherwise limited to Manage Values rename/merge/delete.
- Finance-domain values are stored in lowercase; notes preserve case. Search is case-insensitive.
- Use existing values whenever possible; creation is allowed only in explicit contexts
  (transaction entry, tag assignment, and Manage Values rename/merge).
- Tag names cannot contain commas to ensure CSV round-tripping.
- Missing payer/payee/payment_type are stored as NULL; filters can select "Missing (NULL)".
- Payer must always differ from payee; operations that would violate this are blocked with a warning.
- Selected database path and configured import/export/backup directories persist across sessions
  via a small settings SQLite DB stored alongside the active finance DB (gitignored); it
  remembers the last-used DB and up to 3 recent DBs.
- UI theme uses Streamlit's native setting (light/dark/system); the app does not override it.

## Widget Patterns

### P1 Select-or-Create
Single text input with suggestion list. User can pick an existing value or type a new one.
- UI: text_input + filtered suggestions list.
- Behavior: creation happens only on form submit; show a "will create new value" preview if the input
  does not match an existing value.
- Input is normalized (trim + lowercase) before comparison and preview.
- For nullable fields, include an explicit "(none)" choice to store NULL.
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
- Sidebar label for the main page is "HOME"; top header reads "Home" with a matching anchor.
- Database selection:
  - Default path from environment.
  - Recent DB list (max 3) plus manual path input to override.
  - Allow creating a new empty DB if the path does not exist (default under data dir).
  - Persist selection across sessions and load the chosen database on startup.
  - Switching DBs resets session filters/state and shows a confirmation.
- Configuration section for import/export/backup directories (editable, persisted in settings DB).

### Tutorial
Purpose: README-style onboarding and comparison explainer.
- README-style tutorial section (headers, text, bullets) with a comparison logic explainer;
  optional images; final content defined later.

### Transactions
Purpose: view and maintain transactions.
- Search: free-text input at the top; filters by payer, payee, category, subcategory, tags,
  and notes.
- List view: scrollable table directly below search with all filtered transactions and all
  fields as columns; default column order is id, date_payment, date_application, payer, payee,
  amount_cents, category, subcategory, notes, tags, payment_type; column display labels are
  id, Date payment, Date application, Payer, Payee, Amount (amount_cents/100), Category,
  Subcategory, Notes, Tags, Payment type; tags shown as a comma-separated, lexicographically
  sorted list; allow column hide/show; default order is date_application desc, id desc; user
  can sort by clicking column headers in the table; no separate sort menu or pagination in MVP.
- Filters (P2/P3b) appear below the table: date range, payer, payee, category, subcategory,
  payment_type, tags.
- Date range filter applies to date_application (no selector in MVP).
- Missing-value toggles: include missing payer, payee, or payment_type.
- Subcategory choices are filtered by the selected category.
- If any tags are selected, untagged transactions are excluded.
- Multiple selected tags use ANY semantics (match any selected tag).
- Add transaction (form):
  - Fields: date_payment, date_application, amount, payer, payee, category, subcategory,
    payment_type, notes, tags.
  - Use P1 for payer/payee/category/subcategory/payment_type.
  - Use P3a for tags.
  - Subcategory suggestions are scoped to the selected category.
  - If only one date is provided, auto-copy it into the other field before save.
- Edit transaction (one at a time): same fields as add.
- Delete transaction: confirmation required.

### Transactions-plus (Experimental)
Purpose: inline editing with bulk saves while keeping the original Transactions workflow intact.
- Layout:
  - Search input at the top.
  - Visible columns selector directly above the table.
  - Editable table below (approx. 15 visible rows; scroll to view all results).
  - Filters appear below the table (same filters as Transactions).
- Table behavior:
  - Column sorting via header clicks remains enabled.
  - All fields editable except `id`.
  - In-table add/remove is allowed with explicit save; deletions require confirmation.
  - Bulk edits across non-contiguous rows are allowed.
  - Save changes is explicit and all-or-nothing; invalid rows block the save.
  - Provide a short note near the table explaining that subcategory suggestions are not
    row-scoped; selections are validated on save (must match the row’s category).
- Suggestions + creation:
  - payer/payee/category/subcategory/payment_type use dropdown suggestions from existing values.
  - A small “add new value” helper lets users add a new option to the dropdown list before saving.
- Tags:
  - Use a multiselect-style editor in the table; allow new tags; normalize on save.
  - Tags shown as a list in the table editor.
- Forms:
  - Keep single-transaction Add/Edit/Delete forms below for safe one-at-a-time operations.
  - Delete requires confirmation (checkbox).

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
  - Quick range toggles: "Full period" (min/max dates) and "Full year" (select a year and use Jan 1–Dec 31).
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
  - Each period can toggle "Full year" to select a single year (Jan 1–Dec 31).
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
      - Disambiguate labels (e.g., `category:food`, `tag:food`) to avoid collisions.
  - Subcategory nodes are category-scoped (category + subcategory pairs).
  - "All categories" and "All tags" are total slices (no category or tag filter).
  - Selected nodes are evaluated independently; UI produces one output block per node.
  - TagMatch ANY/ALL applies only in category slices + tag filter mode.
- Output:
  - Results table and grouped bar charts.
  - Tables are per period and node: rows are groups; columns are #tx (inflow ∪ outflow), inflow,
    outflow, and net in role mode, or #transactions and matched flow in matched-only mode.
  - Charts are shown per group as a horizontal row of per-node bar charts (periods on x-axis),
    each with its own y-scale to avoid flattening small nodes.
