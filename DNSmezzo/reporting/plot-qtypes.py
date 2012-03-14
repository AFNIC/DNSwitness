#!/usr/bin/python
# -*- coding: utf-8 -*-

import psycopg2
import locale
import time
import Utils

encoding = "UTF-8"
sniffer = "jezabel"

conn = psycopg2.connect("dbname=dnsmezzo3")
cursor = conn.cursor()

interesting_qtypes = {1: 'A', 2: 'NS', 15: 'MX', 28: 'AAAA'}

def by_type (l, r):
    l = int(l)
    r = int(r)
    if l < r:
        return -1
    elif l > r:
        return 1
    else:
        return 0

for (last_sunday_id, last_tuesday_id, last_tuesday_date) in \
        Utils.get_set_days(cursor, sniffer):
    # TODO: validity control, that the id exists and that there is < 10 days between the dates
    cursor.execute("""SELECT count(results.id) FROM 
             (SELECT id, qtype FROM dns_packets 
                  WHERE (file=%(sunday)s OR file=%(tuesday)s) AND query) AS Results
        """,  {'sunday': last_sunday_id, 'tuesday': last_tuesday_id})
    total = int(cursor.fetchone()[0])
    cursor.execute("""
       SELECT qtype,
          count(results.id) AS requests FROM 
             (SELECT id, qtype FROM dns_packets 
                  WHERE (file=%(sunday)s OR file=%(tuesday)s) AND query) AS Results
              GROUP BY qtype ORDER BY qtype;
              """,
                   {'sunday': last_sunday_id, 'tuesday': last_tuesday_id})
    values = {}
    for tuple in cursor.fetchall():
        qtype = int(tuple[0])
        requests = int(tuple[1])
        values[qtype] = requests
    line = last_tuesday_date.strftime("%d/%m/%Y")
    interesting_qtypes_values = interesting_qtypes.keys()
    interesting_qtypes_values.sort(by_type)
    for qtype in interesting_qtypes_values:
        try:
            line += (" %2.2f" % (float(values[qtype])*100/total))
            del values[qtype]
        except KeyError:
            line += " 0.0"
    remaining = 0
    for qtype in values:
        remaining += values[qtype]
    line += (" %2.2f" % (float(remaining*100)/total))
    print line

conn.close()
