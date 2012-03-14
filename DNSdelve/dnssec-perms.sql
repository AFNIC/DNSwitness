GRANT SELECT,INSERT ON Zones, Tests, Tests_keys, Keys TO dnsdelve;
GRANT SELECT,UPDATE ON Zones_id_seq, Tests_id_seq, Keys_id_seq TO dnsdelve;

\i runs-perms.sql

