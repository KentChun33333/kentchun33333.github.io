-- Counterparties in the review period, per direction, with whether they bank with us.
SELECT t.counterparty,
       t.counterparty_country AS country,
       t.direction,
       COUNT(*) AS txns,
       ROUND(SUM(t.amount_sgd), 2) AS total_sgd,
       group_concat(DISTINCT t.ccy) AS ccy,
       MIN(t.value_date) AS first_date,
       MAX(t.value_date) AS last_date,
       MAX(t.counterparty_bank) AS bank,
       CASE WHEN c.cif IS NULL THEN 'no' ELSE 'yes' END AS bank_customer
  FROM transactions t
  JOIN accounts a ON a.account_no = t.account_no
  LEFT JOIN customers c ON upper(c.name) = upper(t.counterparty)
 WHERE a.cif = :cif
   AND t.value_date BETWEEN :lookback_date AND :start_date
   AND t.counterparty <> ''
   AND t.type NOT IN ('Charges', 'FX transfer', 'Payroll')
 GROUP BY t.counterparty, t.direction
 ORDER BY total_sgd DESC
