# Data Dictionary

This document is the single source of truth for persisted fields and their meanings.
It covers both the finance database and the app settings database.

## Conventions
- All text values are trimmed and stored in lowercase.
- Empty strings become NULL for nullable fields.
- Dates use ISO format YYYY-MM-DD.
- Amounts are stored as integer cents (non-negative; 0 allowed).
- Payer and payee must never be equal, and cannot both be NULL.
- If only one of date_payment or date_application is provided, the other is copied from it.

## Finance DB (finance.db)

### transactions
Core transaction records. Amount always flows from payer to payee.

- id
  - Type: INTEGER PRIMARY KEY
  - Meaning: unique transaction identifier
- date_payment
  - Type: TEXT NOT NULL
  - Meaning: date the payment was made
  - Validation: YYYY-MM-DD; required
- date_application
  - Type: TEXT NOT NULL
  - Meaning: date the payment was applied/posted
  - Validation: YYYY-MM-DD; required
- amount_cents
  - Type: INTEGER NOT NULL
  - Meaning: absolute amount in cents (no sign)
  - Validation: integer >= 0
- payer
  - Type: TEXT NULL
  - Meaning: party sending money
  - Validation: trimmed, lowercase; NULL allowed; cannot equal payee; cannot both be NULL
- payee
  - Type: TEXT NULL
  - Meaning: party receiving money
  - Validation: trimmed, lowercase; NULL allowed; cannot equal payer; cannot both be NULL
- category
  - Type: TEXT NOT NULL
  - Meaning: primary category
  - Validation: trimmed, lowercase; required
- subcategory
  - Type: TEXT NULL
  - Meaning: optional subcategory under category
  - Validation: trimmed, lowercase; NULL allowed
- payment_type
  - Type: TEXT NULL
  - Meaning: free-text payment type (e.g., card, transfer)
  - Validation: trimmed, lowercase; NULL allowed
- notes
  - Type: TEXT NULL
  - Meaning: user notes
  - Validation: trimmed, lowercase; NULL allowed

### tags
Normalized tag list.

- id
  - Type: INTEGER PRIMARY KEY
  - Meaning: unique tag identifier
- name
  - Type: TEXT NOT NULL UNIQUE
  - Meaning: tag name
  - Validation: trimmed, lowercase; unique

### transaction_tags
Many-to-many join between transactions and tags.

- transaction_id
  - Type: INTEGER NOT NULL (FK to transactions.id)
  - Meaning: related transaction
- tag_id
  - Type: INTEGER NOT NULL (FK to tags.id)
  - Meaning: related tag
- Primary key: (transaction_id, tag_id)

## Derived (Not Stored)
- amount_display: string formatted as decimal with "." and two digits (e.g., 5.01)
- tags list: derived from tags and transaction_tags
- comparison selections (periods, groups, nodes) are UI-only

## App Settings DB (app_settings.db)
Stored in the data directory to persist across sessions and containers.

### app_settings
Single-row table (id = 1).

- id
  - Type: INTEGER PRIMARY KEY
  - Meaning: singleton row identifier (always 1)
- last_used_db_path
  - Type: TEXT NULL
  - Meaning: last selected finance DB path
- theme
  - Type: TEXT NOT NULL
  - Meaning: UI theme, one of "light" or "dark"

### recent_db_paths
Tracks up to the three most recent DB paths.

- path
  - Type: TEXT PRIMARY KEY
  - Meaning: finance DB path
- last_used_at
  - Type: INTEGER NOT NULL
  - Meaning: unix epoch seconds used for recency ordering
