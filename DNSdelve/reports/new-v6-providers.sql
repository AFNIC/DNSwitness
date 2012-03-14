-- Find out the new IPv6 addresses, that were not them in the last run.
-- Caution: sampling can make infrequent addresses appear and disappear
SELECT DISTINCT address, count (*) AS occurrences FROM Hosts 
         WHERE uuid='edd18db4-0898-41f7-bbe8-40cef52f91aa' AND 
         address NOT IN (SELECT address FROM Hosts 
                            WHERE uuid='9e9ab518-cdc3-4974-aa5b-496720cfc918') 
    GROUP BY address ORDER BY occurrences DESC;

-- Keep only the prefixes
-- http://www.postgresql.org/docs/current/static/functions-net.html
SELECT DISTINCT set_masklen(address::cidr, 32) AS prefix, count (*) AS occurrences FROM Hosts 
         WHERE uuid='edd18db4-0898-41f7-bbe8-40cef52f91aa' AND 
         address NOT IN (SELECT address FROM Hosts 
                            WHERE uuid='9e9ab518-cdc3-4974-aa5b-496720cfc918') 
    GROUP BY prefix ORDER BY occurrences DESC;

-- Using the date. You look at the graph and estimates the dates:
SELECT DISTINCT set_masklen(address::cidr, 32) AS prefix, count (*) AS occurrences 
     FROM Hosts 
         WHERE uuid IN 
             (SELECT uuid FROM Runs WHERE date > '2009-06-03' AND date < '2009-06-07')
           AND 
            address NOT IN (SELECT address FROM Hosts 
                            WHERE uuid IN 
                                (SELECT uuid FROM Runs WHERE date > '2009-05-23' AND 
                                                             date < '2009-05-29'))
    GROUP BY prefix ORDER BY occurrences DESC;

-- Using an utility script, you just have to indicate the date once
psql -c " SELECT DISTINCT set_masklen(address::cidr, 32) AS prefix, count (*) AS occurrences   FROM Hosts $(reports/interval.py 2009-08-01 dnswitness-ipv6) GROUP BY prefix ORDER BY occurrences DESC;" dnswitness-ipv6 
