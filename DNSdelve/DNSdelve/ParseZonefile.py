#!/usr/bin/python

""" Parses a DNS zone file (format - poorly - described in RFC 1035,
section 5, and implemented by BIND, NSD and a few others)."""

import re
import string

# We assume LDH domains, which is questionable.
ldh_name = "[a-z0-9\.-]+"
# This regexp is too lax, it can accept two TTLs...
ns_record = re.compile("^(%s)?(\s+[0-9]+)?(\s+IN)?(\s+[0-9]+)?\s+NS\s+(%s)" % (ldh_name, ldh_name))

def parse(filename):
    """ Parses a DNS zone file and returns a dictionary of zones with
    their nameservers as an array."""
    zones = {}
    lineno = 0
    file = open(filename)
    current_domain = None
    for line in file:
        lineno = lineno + 1
        match = re.match(ns_record, line)
        if match:
            if match.group(1):
                domain = match.group(1)
                current_domain = domain
            else:
                if current_domain is None:
                    raise Exception("No current domain at line %i" % lineno)
                domain = current_domain
            # Canonicalisation of the domain name
            domain = string.lower(domain)
            domain = re.sub("\.$", "", domain)
            if zones.has_key(domain):
                zones[domain].append(match.group(5))
            else:
                zones[domain] = [match.group(5),]
        else:
            pass # Yes, that's poor parsing, we ignore any other line!
    return zones

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print >>sys.stderr, "Usage: %s zonefile" % sys.argv[0]
        sys.exit(1)
    filename = sys.argv[1]
    zones = parse(filename)
    print zones
    
