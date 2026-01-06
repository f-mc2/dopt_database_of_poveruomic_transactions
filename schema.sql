CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY,
  date_payment TEXT NOT NULL,
  date_application TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
  payer TEXT NULL,
  payee TEXT NULL,
  payment_type TEXT NULL,
  category TEXT NOT NULL,
  subcategory TEXT NULL,
  notes TEXT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK (payer IS NULL OR payee IS NULL OR payer <> payee)
);

CREATE INDEX IF NOT EXISTS idx_transactions_date_payment
  ON transactions(date_payment);

CREATE INDEX IF NOT EXISTS idx_transactions_date_application
  ON transactions(date_application);

CREATE INDEX IF NOT EXISTS idx_transactions_category_subcategory
  ON transactions(category, subcategory);

CREATE INDEX IF NOT EXISTS idx_transactions_payer
  ON transactions(payer);

CREATE INDEX IF NOT EXISTS idx_transactions_payee
  ON transactions(payee);

CREATE TABLE IF NOT EXISTS tags (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS transaction_tags (
  transaction_id INTEGER NOT NULL,
  tag_id INTEGER NOT NULL,
  PRIMARY KEY (transaction_id, tag_id),
  FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
  FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);
