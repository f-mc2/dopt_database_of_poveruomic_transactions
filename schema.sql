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
  CHECK (length(trim(category)) > 0 AND category = lower(trim(category))),
  CHECK (payer IS NULL OR (length(trim(payer)) > 0 AND payer = lower(trim(payer)))),
  CHECK (payee IS NULL OR (length(trim(payee)) > 0 AND payee = lower(trim(payee)))),
  CHECK (
    subcategory IS NULL OR (length(trim(subcategory)) > 0 AND subcategory = lower(trim(subcategory)))
  ),
  CHECK (
    payment_type IS NULL OR (length(trim(payment_type)) > 0 AND payment_type = lower(trim(payment_type)))
  ),
  CHECK (notes IS NULL OR length(trim(notes)) > 0),
  CHECK (
    date_payment GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]' AND
    date(date_payment) IS NOT NULL AND date(date_payment) = date_payment
  ),
  CHECK (
    date_application GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]' AND
    date(date_application) IS NOT NULL AND date(date_application) = date_application
  ),
  CHECK (payer IS NOT NULL OR payee IS NOT NULL),
  CHECK (payer IS NULL OR payee IS NULL OR payer <> payee)
);

CREATE INDEX IF NOT EXISTS idx_transactions_date_payment
  ON transactions(date_payment);

CREATE INDEX IF NOT EXISTS idx_transactions_date_application
  ON transactions(date_application);

CREATE INDEX IF NOT EXISTS idx_transactions_category
  ON transactions(category);

CREATE INDEX IF NOT EXISTS idx_transactions_subcategory
  ON transactions(subcategory);

CREATE INDEX IF NOT EXISTS idx_transactions_payer
  ON transactions(payer);

CREATE INDEX IF NOT EXISTS idx_transactions_payee
  ON transactions(payee);

CREATE INDEX IF NOT EXISTS idx_transactions_payment_type
  ON transactions(payment_type);

CREATE TABLE IF NOT EXISTS tags (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
    CHECK (
      length(trim(name)) > 0
      AND instr(name, ',') = 0
      AND name = lower(trim(name))
    )
);

CREATE TABLE IF NOT EXISTS transaction_tags (
  transaction_id INTEGER NOT NULL,
  tag_id INTEGER NOT NULL,
  PRIMARY KEY (transaction_id, tag_id),
  FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
  FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_transaction_tags_transaction_id
  ON transaction_tags(transaction_id);

CREATE INDEX IF NOT EXISTS idx_transaction_tags_tag_id
  ON transaction_tags(tag_id);
