#!/usr/bin/env python

# Display various statistics about the number of name servers per zone
# in a delegation zone file

import ParseZonefile
import sys

def median(zlist):
    list = zlist.keys()
    list.sort(cmp= lambda x,y: cmp(zones[x], zones[y]))
    return len(zones[list[int(len(list)/2)]])

if len(sys.argv) != 2:
    print >>sys.stderr, "Usage: %s zonefile" % sys.argv[0]
    sys.exit(1)
filename = sys.argv[1]
zones = ParseZonefile.parse(filename)

minimum = 9999
maximum = 0
totalns = 0
buckets = {}
totalzones = len(zones)
for zone in zones:
    nns = len(zones[zone])
    if not buckets.has_key(nns):
        buckets[nns] = 1
    else:
        buckets[nns] += 1
    if nns < minimum:
        minimum = nns
    if nns > maximum:
        maximum = nns
    totalns += nns
print "%i zones, min. number of NS %i, max. number %i, average %.2f, median %i" % \
      (totalzones, minimum, maximum, float(totalns)/float(totalzones), median(zones))
for i in range(0, 13):
    if buckets.has_key(i):
        num = buckets[i]
    else:
        num = 0
    print "%i nameservers: %i zones (%i %%)" % \
          (i, num, int(float(num)*100/float(totalzones)))
