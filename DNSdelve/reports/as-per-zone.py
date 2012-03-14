#!/usr/bin/python

import sys
import time
import psycopg2

dbinfo_default = "dbname=dnsdelve-ip"

if len(sys.argv) < 2 or len(sys.argv) > 3:
    print >>sys.stderr, "Usage: %s uuid [dbinfo]" % sys.argv[0]
    sys.exit(1)

uuid = sys.argv[1]
if len(sys.argv) == 3:
    dbinfo = sys.argv[2]
else:
    dbinfo = dbinfo_default

conn = psycopg2.connect(dbinfo)
cursor = conn.cursor()
cursor.execute("""
  SELECT count(distinct z.zone) FROM Broker b, Zones z WHERE b.uuid = '%s' AND z.id=b.zone;
""" % uuid)
total = int(cursor.fetchone()[0])
cursor.execute("""
  SELECT distinct  z.zone, count (distinct t.asn) FROM Tests_ns_zone t, Broker b, Zones z WHERE b.uuid = '%s' AND t.broker = b.id  AND z.id=b.zone GROUP BY z.zone;
""" % uuid)
total_asns = 0
more_than_two = 0
exactly_two = 0
only_one = 0
max = 0
for tuple in cursor.fetchall():
    num_asns = int(tuple[1])
    if num_asns <= 0:
        # raise Exception("Invalid number of AS for zone %s" % tuple[0])
        pass # Sometimes, we cannot fetch AS info for an address (bogon?)
    total_asns += num_asns
    if num_asns > 2:
        more_than_two += 1
    elif num_asns == 2:
        exactly_two += 1
    else:
        only_one += 1
    if num_asns > max:
        max = num_asns
cursor.close()
conn.close()
print "%i zones" % total
print "%i zones with > 2 AS" % more_than_two
print "%i zones with 2 AS" % exactly_two
print "%i zones with only 1 AS" % only_one
print "Average number of AS %.2f" % (float(total_asns)/float(total))
print "Maximum number of AS %i" % max

