-- How to obtain the top non-existing domains

SELECT DISTINCT substr(registered_domain,1,43) AS domain,count(registered_domain) AS num FROM DNS_packets WHERE file=3 AND NOT query AND rcode= 3 GROUP BY registered_domain ORDER BY count(registered_domain) DESC;
