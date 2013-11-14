#!/bin/sh


psql -a -f create-databases.sql


psql -d dnswitness-dnssec -a -f dnssec-create.sql
psql -d dnswitness-dnssec -a -f dnssec-update.sql
psql -d dnswitness-dnssec -a -f dnssec-perms.sql

psql -d dnswitness-spf -a -f spf-create.sql
psql -d dnswitness-spf -a -f spf-perms.sql

psql -d dnsdelve-ip -a -f ip-create.sql
psql -d dnsdelve-ip -a -f ip-perms.sql

psql -d dnsdelve-redirections -a -f redirections-create.sql
psql -d dnsdelve-redirections -a -f redirections-perms.sql

psql -d dnsdelve-zonecheck -a -f zonecheck-create.sql

