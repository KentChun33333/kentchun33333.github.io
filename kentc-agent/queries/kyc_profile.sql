-- KYC profile of the case customer: one row (each column becomes a key value).
SELECT c.cif,
       c.name,
       c.business,
       c.incorporated,
       c.risk_rating,
       c.last_review,
       c.rm,
       c.expected_monthly_inflow_sgd,
       (SELECT group_concat(p.name || ' (' || p.role || COALESCE(', ' || CAST(p.share_pct AS INTEGER) || '%', '') || ')', '; ')
          FROM related_parties p WHERE p.cif = c.cif) AS directors_owners,
       (SELECT group_concat(a.ccy || ' ' || a.type || ' ' || a.account_no || ', opened ' || a.opened || ' - ' || a.purpose, '; ')
          FROM accounts a WHERE a.cif = c.cif) AS accounts
  FROM customers c
 WHERE c.cif = :cif
