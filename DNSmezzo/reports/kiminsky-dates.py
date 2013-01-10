#!/usr/bin/python

# Find client resolvers which are not patched against the Kaminsky bug
# in a time interval.

dbinfo = "dbname=dnsmezzo"
MIN_REQUESTS = 10
MIN_RATIO = 0.4

import psycopg2
import sys
import math

def by_ratio (l, r):
    if clients[l] < clients[r]:
        return -1
    elif clients[l] > clients[r]:
        return +1
    else:
        return 0

if len(sys.argv) <= 2:
    raise Exception("Usage: %s date-start date-end ..." % sys.argv[0])

datestart = sys.argv[1]
dateend   = sys.argv[2]

datestuff = "AND (date BETWEEN '%s' AND '%s')" % (datestart,  dateend)

conn = psycopg2.connect(dbinfo)
cursor = conn.cursor()
cursor.execute("""
  SELECT src_address AS resolver, count(id) AS requests, count(DISTINCT src_port) AS ports 
  FROM DNS_Packets WHERE query AND NOT rd %s
         GROUP BY resolver ORDER BY requests;
  """ % datestuff)
clients = {}
cl_ports = {}
cl_requests = {}
num_vulnerable = 0
requests_vulnerable = 0
num_kept = 0
requests_kept = 0
for client in cursor.fetchall():
    requests = int(client[1])
    ports = int(client[2])
    if requests < MIN_REQUESTS:
        continue
    num_kept += 1
    requests_kept += requests
    if requests > (65536-1024): # Maximum number of ports one can reasonably use
        capped_requests = 65536-1024
    else:
        capped_requests = requests
    ratio = float(ports) / float(capped_requests) 
    if ratio < MIN_RATIO:
        num_vulnerable += 1
        requests_vulnerable += requests
        clients[client[0]] = ratio
        cl_ports[client[0]] = ports
        cl_requests[client[0]] = requests
sorted_clients = clients.keys()
sorted_clients.sort(by_ratio)
print """%2.2f %% of clients with more than %i requests are vulnerable to the Kaminsky attack 
     (have less than %1.2f ports per capped request)
     They make %2.2f %% of the requests.""" % \
    (float(num_vulnerable)*100.0/float(num_kept), MIN_REQUESTS, MIN_RATIO,
     float(requests_vulnerable)*100.0/float(requests_kept))
for client in sorted_clients:
    print "%s: %2.4f (%i ports, %i requests)" % \
        (client, clients[client], cl_ports[client], cl_requests[client])
