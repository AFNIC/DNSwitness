SELECT src_address, count(id) AS requests FROM DNS_packets WHERE file >= 480 AND query 
   GROUP BY src_address ORDER by requests DESC;
