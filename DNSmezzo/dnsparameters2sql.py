#!/usr/bin/python

""" 

Converts the IANA dns-parameters file (at least a part of it) to SQL.

It would be much better if this file were in XML :-(

"""

import re
from psycopg2.extensions import adapt

input = open("dns-parameters") # http://www.iana.org/assignments/dns-parameters
start = False
print "DELETE FROM DNS_types;"
for line in input:
    if re.search("TYPE\s+Value and meaning\s+Reference", line):
        start = True
    if start:
        if re.search("Reserved\s+65535", line):
            start = False
        match = re.search("^([A-Z0-9\*]+)\s+([0-9]+)\s+(.*?)\s+([RFC0-9\[\]]+)$", line)
        #match = re.search("^([A-Z]+)\s+([0-9]+)\s+(.*?)\s+([RFC])", line)
        if match:
            print """INSERT INTO DNS_types (type, value, meaning, rfcreferences) 
                           VALUES (%s, %s, %s, %s);""" % \
                (adapt(match.group(1)), match.group(2), 
                 adapt(match.group(3)), adapt(match.group(4)))
            # http://stackoverflow.com/questions/309945/how-to-quote-a-string-value-explicitly-python-db-apipsycopg2
input.close()
