#!/usr/bin/python

""" Parses a list of domain names - they must be written one by line. """

import re
import string

# We assume LDH domains, which is questionable.
ldh_name = "^\s*([a-zA-Z0-9\.-]+)\s*$"

def parse(filename):
    """ Parses a plain text file and returns a dictionary of zones with
    their nameservers as an array - always empty since we only have the domains."""
    zones = {}
    lineno = 0
    file = open(filename)
    current_domain = None
    for line in file:
        lineno = lineno + 1
        match = re.match(ldh_name, line)
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
            zones[domain] = True
        else:
            pass # Yes, that's poor parsing, we ignore any other line!
    return zones

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print >>sys.stderr, "Usage: %s file" % sys.argv[0]
        sys.exit(1)
    filename = sys.argv[1]
    zones = parse(filename)
    print zones
    
