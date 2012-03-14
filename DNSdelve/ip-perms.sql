-- UPDATE right (or DELETE) is mandatory to lock the table http://www.postgresql.org/docs/8.4/static/sql-lock.html

GRANT SELECT,INSERT ON Zones, Tests, Ip, Broker, tests_zone, tests_ns_zone, tests_mx_zone, tests_www_zone, tests_www_ipv6_zone TO dnsdelve;
GRANT SELECT,UPDATE ON Zones, Ip, Zones_id_seq, Tests_id_seq, Ip_id_seq, Broker_id_seq TO dnsdelve;

\i runs-perms.sql
