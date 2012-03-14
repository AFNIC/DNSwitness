#!/bin/sh

# A very crude equivalent of DNSdelve. Purely sequential

# List of domains, one per line
DOMAINS="domains.txt"

# Here, we look for SPF records, encoded in TXT records

for domain in $(cat $DOMAINS); do
    echo ""
    echo $domain
    # isc.org has a TXT which is not SPF
    dig +short TXT $domain | grep "v=spf1"
done
