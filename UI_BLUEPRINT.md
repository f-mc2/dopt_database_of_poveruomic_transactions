# UI Blueprint

## Global Layout and Rules
- Streamlit multipage navigation in the sidebar.
- Desktop-first layout with mobile-safe stacking.
- Destructive actions always require explicit confirmation.
- No bulk edit/delete of transactions; only one-at-a-time edits.
- Field values are stored in lowercase; search is case-insensitive.
- Use existing values whenever possible; creation is allowed only in explicit contexts
  (transaction entry and tag assignment).
- Missing payer/payee/payment_type are stored as NULL; NULL values are not selectable in filters.
- Payer must always differ from payee; operations that would violate this are blocked with a warning.
- Selected database path and UI theme persist across sessions via a small settings SQLite DB
  stored in the data directory (gitignored); it remembers last-used DB and up to 3 recent DBs.

## Widget Patterns

### P1 Select-or-Create
Single text input with suggestion list. User can pick an existing value or type a new one.
- UI: text_input + filtered suggestions list.
- Behavior: if user clicks a suggestion, the input is filled; otherwise, the input creates a new value.
- Use for: transaction entry fields (payer, payee, category, subcategory, payment_type) and tag creation.

### P2 Select-Existing-Only
Typeahead search + selectbox over filtered existing values (no creation).
- UI: text_input for search, then selectbox of filtered values.
- Use for: filters, comparison selectors, manage-values selectors.

### P3a Tags Assign
Assign tags to a transaction with the option to add new tags.
- UI: multiselect of existing tags + text_input to add a new tag.
- Behavior: add input value to tag list if new, then include it in selection.

### P3b Tags Filter
Filter by tags from existing values only.
- UI: multiselect with search/filter.
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
- Show configured import/export/backup directories.

### Transactions
Purpose: view and maintain transactions.
- Filters (P2/P3b): date range, payer, payee, category, subcategory, payment_type, tags.
- List view: table of transactions with pagination or "show N latest".
- Add transaction (form):
  - Fields: date_payment, date_application, amount, payer, payee, category, subcategory,
    payment_type, notes, tags.
  - Use P1 for payer/payee/category/subcategory/payment_type.
  - Use P3a for tags.
- Edit transaction (one at a time): same fields as add.
- Delete transaction: confirmation required.

### Import/Export
Purpose: CSV import, export, and backup.
- Import:
  - File uploader for semicolon-separated CSV.
  - Validate required columns (amount, date_payment, date_application, category, and one of payer/payee).
  - Abort on any invalid row; no partial inserts.
- Export:
  - Required date range selection.
  - Optional filters using P2/P3b.
  - Download button; optional save to configured export directory.
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
- Any operation that would result in payer == payee is blocked with a warning.

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
- Node selection (categories/subcategories and tags):
  - Choose AND or OR composition.
  - AND mode:
    - Select up to 10 category/subcategory nodes (P2) with an "All categories" option.
    - Select tags (P3b). Tag match uses ANY or ALL.
  - OR mode:
    - Select up to 10 nodes across category/subcategory/tags (P2) with "All categories" and
      "All tags" options.
- Output:
  - Results table and grouped bar charts.
