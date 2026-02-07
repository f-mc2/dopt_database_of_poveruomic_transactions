# Database of Poveruomic Transactions

Local-first, single-user finance tracker built with Streamlit and SQLite. It stores data
in a future-proof database + CSV format and focuses on flexible comparisons across years,
people, and categories.

## Vibecoding note
This project is intentionally fully vibecoded. The codebase and all documentation
(including this README and everything in `docs/`) are written with the Codex VS Code
extension after extensive discussions and iterations.

## Motivation
I used HomeBank for years but struggled to compare spending on groceries, utilities, and
similar categories across different years. I also wanted more control, a local-first
workflow, and a future-proof data format. This project lets me define my own comparison
logic, keep everything in a SQLite database, and learn Python through vibecoding while
building something useful for tracking household and hobby spending over time.

## Quick start (local)
1. Create and activate a virtual environment.
2. Install dependencies.
3. Run the app with Streamlit.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Defaults:
- Finance DB: `./data/finance.db` (gitignored)
- CSV import dir: `./data/csv_import`
- CSV export dir: `./data/csv_export`
- DB backup dir: `./data/db_backup`

Override with env vars:
- `DOPT_DB_PATH`
- `DOPT_CSV_IMPORT_DIR`
- `DOPT_CSV_EXPORT_DIR`
- `DOPT_DB_BACKUP_DIR`

## How to use the app
- Home: open or create a finance DB and see key stats.
- Transactions-legacy: add/edit one transaction at a time; tags and normalized fields are enforced.
- Transactions: bulk inline edits with explicit save and validation.
- Import/Export: semicolon-separated CSV import; filtered export with tags column.
- Manage Values: rename or merge payers, payees, categories, subcategories, tags.
- Compare: configure periods, groups, and slices to analyze trends.

## Comparison logic (detailed)
The comparison engine is built around three concepts: periods, groups, and nodes.

### Periods
You can define up to 5 periods. Each period has:
- a label
- a date range (start/end, inclusive), or a full year (Jan 1 to Dec 31)
- a date field selector (`date_application` or `date_payment`)

### Groups
Each group has two sets:
- A = payers
- B = payees

Groups let you compare different people or scopes. Example:
- "family" group: A = {alice, bob}, B = {alice, bob}
- "alice" group: A = {alice}, B = {alice}

### Nodes (slices)
Nodes define what you are slicing by. There are two slice modes:

1) Category slices + tag filter (AND mode)
- Choose up to 10 category/subcategory nodes.
- Apply an optional tag filter with TagMatch ANY or ALL.
- TagMatch applies to every selected node.

2) Mixed slices (OR mode)
- Choose up to 10 nodes across category, subcategory, tags, and totals.
- Totals are `all_categories` and `all_tags`.
- Nodes are evaluated independently.
- Labels are disambiguated (e.g., `category:food`, `tag:food`).

### Modes
For each period P, group G=(A,B), and node N:

Role mode:
- Outflow = sum where payer in A and node matches.
- Inflow = sum where payee in B and node matches.
- Net = inflow - outflow.
- #tx = distinct transactions where payer in A OR payee in B and node matches.

Matched-only mode:
- Matched flow = sum where payer in A AND payee in B and node matches.
- #tx = distinct matched transactions.

### TagMatch behavior (AND mode)
- ANY: transaction has at least one selected tag.
- ALL: transaction has all selected tags.
- If tag list is empty, TagMatch is true.
- If tags are selected, untagged transactions are excluded.

## Comparison examples

### Example 1: Year-over-year concert tickets (role mode)
Goal: compare live-music ticket spending across years.

Setup:
- Periods: 2022, 2023 (full years)
- Group "me": A = {zalmosside}, B = {zalmosside}
- Slice mode: category slices
- Nodes: `concert_tickets`

Selected transactions in 2022:
- 2022-01-22, amount 35.00, payer=zalmosside, payee=venue_a, category=concert_tickets
- 2022-03-19, amount 48.00, payer=zalmosside, payee=boxoffice, category=concert_tickets
- 2022-06-05, amount 90.00, payer=zalmosside, payee=festival_org, category=concert_tickets
- 2022-10-14, amount 60.00, payer=zalmosside, payee=venue_b, category=concert_tickets
- 2022-12-02, amount 52.00, payer=zalmosside, payee=ticket_platform, category=concert_tickets

Result for 2022:
- Outflow = 285.00 (five ticket purchases by group payers)
- Inflow = 0.00 (no ticket transactions paid to group payees)
- Net = -285.00
- #tx = 5

Selected transactions in 2023:
- 2023-02-15, amount 38.00, payer=zalmosside, payee=venue_a, category=concert_tickets
- 2023-03-03, amount 55.00, payer=zalmosside, payee=ticket_platform, category=concert_tickets
- 2023-04-12, amount 72.50, payer=zalmosside, payee=boxoffice, category=concert_tickets
- 2023-06-20, amount 120.00, payer=zalmosside, payee=festival_org, category=concert_tickets
- 2023-07-07, amount 40.00, payer=zalmosside, payee=venue_b, category=concert_tickets
- 2023-09-08, amount 65.00, payer=zalmosside, payee=venue_c, category=concert_tickets
- 2023-11-02, amount 94.00, payer=zalmosside, payee=venue_d, category=concert_tickets

Result for 2023:
- Outflow = 484.50 (seven ticket purchases by group payers)
- Inflow = 0.00 (no ticket transactions paid to group payees)
- Net = -484.50
- #tx = 7

## Docs
- Product brief: `docs/PRODUCT_BRIEF.md`
- PRD: `docs/PRD.md`
- UI blueprint: `docs/UI_BLUEPRINT.md`
- Data dictionary: `docs/DATA_DICTIONARY.md`
- Tech design: `docs/TECH_DESIGN.md`
- Test plan: `docs/TEST_PLAN.md`
