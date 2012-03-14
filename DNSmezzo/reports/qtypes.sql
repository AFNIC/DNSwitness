SELECT (CASE WHEN type IS NULL THEN qtype::TEXT ELSE type END), 
       meaning, 
       count(results.id) AS requests FROM 
             (SELECT id, qtype FROM dns_packets 
                  WHERE file=26 AND query) AS Results
          LEFT OUTER JOIN DNS_types ON qtype = value
              GROUP BY qtype, type, meaning ORDER BY requests desc;

