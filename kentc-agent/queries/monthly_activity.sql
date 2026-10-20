-- Monthly turnover (SGD equivalent) for twelve months before the review period and during it, against the
-- expected monthly inflow in the KYC profile. Own-account FX transfers and bank charges are left out.
SELECT substr(t.value_date, 1, 7) AS month,
       CASE WHEN substr(t.value_date, 1, 7) >= substr(:lookback_date, 1, 7) THEN 'review' ELSE 'baseline' END AS period,
       ROUND(SUM(CASE WHEN t.direction = 'CR' AND t.type <> 'FX transfer' THEN t.amount_sgd ELSE 0 END), 2) AS inflow_sgd,
       ROUND(SUM(CASE WHEN t.direction = 'DR' AND t.type NOT IN ('FX transfer', 'Charges') THEN t.amount_sgd ELSE 0 END), 2) AS outflow_sgd,
       COUNT(*) AS txns,
       c.expected_monthly_inflow_sgd AS expected_inflow_sgd,
       ROUND(SUM(CASE WHEN t.direction = 'CR' AND t.type <> 'FX transfer' THEN t.amount_sgd ELSE 0 END)
             / c.expected_monthly_inflow_sgd, 1) AS x_expected
  FROM transactions t
  JOIN accounts a ON a.account_no = t.account_no
  JOIN customers c ON c.cif = a.cif
 WHERE a.cif = :cif
   AND t.value_date >= date(:lookback_date, '-12 months')
   AND t.value_date <= :start_date
 GROUP BY month
 ORDER BY month
