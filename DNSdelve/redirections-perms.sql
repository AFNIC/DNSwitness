-- UPDATE right (or DELETE) is mandatory to lock the table http://www.postgresql.org/docs/8.4/static/sql-lock.html

GRANT SELECT,INSERT ON URI, Redirect, Crossed_redirections, Crossed_ns, ASN TO dnsdelve;
GRANT SELECT,UPDATE ON URI, ASN, Crossed_ns, uri_id_seq, asn_id_seq, redirect_id_seq, crossed_redirections_id_seq, crossed_ns_id_seq TO dnsdelve;

\i runs-perms.sql
