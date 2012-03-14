-- Find the most often queried domains
-- We exclude MX (type 15) because of spam

SELECT substr(registered_domain,1,46) AS domain, count(id) AS requests FROM dns_packets WHERE file=3 AND query AND qtype != 15
   GROUP BY registered_domain ORDER by requests DESC;

