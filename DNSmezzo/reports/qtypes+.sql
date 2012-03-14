-- WARNING: two parameters to change

SELECT (CASE WHEN type IS NULL THEN qtype::TEXT ELSE type END), 
       meaning, 
       count(results.id)*1000/1615707 AS perthousand FROM 
             (SELECT id, qtype FROM dns_packets 
                  WHERE (file = 20 or file = 22) AND query) AS Results
          LEFT OUTER JOIN DNS_types ON qtype = value
              GROUP BY qtype, type, meaning ORDER BY perthousand desc;
