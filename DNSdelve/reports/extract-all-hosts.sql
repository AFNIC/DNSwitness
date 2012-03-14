#!/bin/sh

DB=dnswitness-ipv6
RUN=2692fbcd-d362-4ce0-875b-48e04c5e8a96 
OPTS=--tuples-only

psql ${OPTS} -c "SELECT domain FROM v6_enabled WHERE uuid='${RUN}'" ${DB} > enabled.txt
psql ${OPTS} -c "SELECT domain FROM v6_full WHERE uuid='${RUN}'" ${DB} > full.txt
psql ${OPTS} -c "SELECT domain FROM v6_web WHERE uuid='${RUN}'" ${DB} > web.txt
psql ${OPTS} -c "SELECT domain FROM v6_email WHERE uuid='${RUN}'" ${DB} > email.txt
psql ${OPTS} -c "SELECT domain FROM v6_dns WHERE uuid='${RUN}'" ${DB} > dns.txt
gzip -9 -v -f *.txt