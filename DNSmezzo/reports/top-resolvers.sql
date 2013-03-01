SELECT src_address, count(id) AS requests FROM DNS_packets WHERE file >= 480 AND query 
   GROUP BY src_address ORDER by requests DESC;

-- or, by prefix

SELECT set_masklen(src_address::cidr, 48) AS prefix, count(id) AS requests FROM DNS_packets WHERE file >= 480 AND query AND  family(src_address)=6
   GROUP BY prefix ORDER by requests DESC;

SELECT set_masklen(src_address::cidr, 26) AS prefix, count(id) AS requests FROM DNS_packets WHERE file >= 480 AND query AND  family(src_address)=4
   GROUP BY prefix ORDER by requests DESC;

-- Quantiles

SELECT n,min(requests),max(requests),
       to_char(sum(requests)*100/(SELECT count(DNS_packets.id) FROM DNS_packets,Pcap_files WHERE (file = pcap_files.id and file >= 485 and filename like '%d.nic.fr%') AND query AND family(src_address)=6), '99.9') AS percentage FROM 
        (SELECT prefix,requests,ntile(10) OVER (ORDER BY requests) AS n FROM 
             (SELECT set_masklen(src_address::cidr, 26) AS prefix, count(dns_packets.id) AS requests FROM
                 DNS_packets,Pcap_files WHERE (file = pcap_files.id and file >= 485 and filename like '%d.nic.fr%') AND query AND  family(src_address)=6          
                GROUP BY prefix ORDER by requests DESC) AS qinternal) AS qexternal 
   GROUP BY n ORDER BY n;