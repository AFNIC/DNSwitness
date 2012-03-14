-- Requests over IPv6
SELECT count(id) FROM DNS_packets WHERE query AND (file = 17 or file = 18) AND family(src_address)=6;

-- Total
SELECT count(id) FROM DNS_packets WHERE query AND (file = 17 or file = 18);

