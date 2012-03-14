-- Find the most often queried domains
-- We exclude the ".fr" nameservers (infraastructure)

SELECT substr(registered_domain,1,46) AS domain, count(id) AS requests FROM dns_packets WHERE (file=5 OR file=13) AND query AND lowercase_qname NOT IN (SELECT name FROM FRzone.nameservers WHERE name=lowercase_qname)
   GROUP BY registered_domain ORDER by requests DESC LIMIT 100;

