-- There are many domains with SPF but identical SPF records may mean
-- a general record added by a povider (or it may mean a popular
-- record such as 'v=spf1 a mx ?all').

SELECT count(spf) AS number, spf AS record FROM Tests WHERE
     uuid='7f66c5e7-cc4f-49ed-b35e-963239025824' AND spf IS NOT NULL
  GROUP BY record ORDER BY number DESC;

