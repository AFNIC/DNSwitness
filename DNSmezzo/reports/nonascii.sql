-- Find requests with a non-ASCII qname

SELECT src_address,qname FROM dns_packets WHERE file=3 AND octet_length(qname) > length(qname);

