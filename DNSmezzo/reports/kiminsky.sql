-- Find resolvers without SPR (Source Port Randomization)
-- TODO: calculate their "badness" with the number of requets (one port is OK if there is only one request!)

SELECT src_address AS resolver,count(id) AS requests, count(DISTINCT src_port) AS ports FROM DNS_Packets WHERE file=55
         GROUP BY resolver 
         ORDER BY ports;

-- Another way to make like kiminsky.py using PGSQL 
SELECT src_address AS resolver, count(id) AS requests, count(DISTINCT src_port) AS ports FROM dns_packets WHERE file=55 AND query 
        GROUP BY resolver 
        HAVING count(id) >= 10 
        ORDER BY requests
