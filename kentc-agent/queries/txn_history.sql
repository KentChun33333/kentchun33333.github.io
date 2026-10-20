-- Every transaction on the customer's accounts in the review period.
SELECT t.value_date, t.account_no, t.ccy, t.type, t.direction, t.amount, t.amount_sgd,
       t.counterparty, t.counterparty_country, t.counterparty_bank, t.channel, t.reference, t.narrative
  FROM transactions t
  JOIN accounts a ON a.account_no = t.account_no
 WHERE a.cif = :cif
   AND t.value_date BETWEEN :lookback_date AND :start_date
 ORDER BY t.value_date, t.txn_id
