-- Without partitioning, this should suffice:
GRANT SELECT, INSERT ON Pcap_files, DNS_packets TO dnsmezzo;
GRANT UPDATE ON Pcap_files TO dnsmezzo;
GRANT SELECT, UPDATE ON Pcap_files_id_seq, DNS_packets_id_seq TO dnsmezzo;

-- Warning: because of partitioning, the owner of the table must be
-- the insertor (otherwise, "must be owner of relation dns_packets"
-- when creating subtables
ALTER TABLE DNS_packets OWNER TO dnsmezzo;
-- Same thing with foreign constraints 
ALTER TABLE Pcap_files OWNER TO dnsmezzo;

