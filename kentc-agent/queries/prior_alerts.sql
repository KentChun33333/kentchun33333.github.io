-- Monitoring and screening alerts on the customer in the 24 months before the start date.
SELECT alert_id, type, scenario, subject, raised, closed, status, disposition
  FROM alerts
 WHERE cif = :cif
   AND raised >= date(:start_date, '-24 months')
 ORDER BY raised DESC
