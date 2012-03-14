#!/usr/bin/python
# -*- coding: utf-8 -*-

import psycopg2
import locale
import time
import sys
import Utils

encoding = "UTF-8"
sniffer = "jezabel"

conn = psycopg2.connect("dbname=dnsmezzo3")
cursor = conn.cursor()
cursor_int = conn.cursor()

# TODO: ignored, decimal numbers are formatted with a dot :-(
locale.setlocale(locale.LC_NUMERIC, "fr_FR.%s" % encoding)

for (last_sunday_id, last_tuesday_id, last_tuesday_date) in \
        Utils.get_set_days(cursor, sniffer, reverse=False):
    # TODO: validity control, that the id exists and that there is < 10 days between the dates
    sys.stdout.write ("%s " % \
        (last_tuesday_date.strftime("%m/%Y")))
    cursor.execute("SELECT DISTINCT length, count(id) FROM dns_packets where (file=%(sunday)s OR file=%(tuesday)s) AND not query GROUP BY length ORDER BY length;", 
                   {'sunday': last_sunday_id, 'tuesday': last_tuesday_id})
    intervals = {'0-127': 0, '128-255': 0, '256-511': 0, '512-1023': 0, 
                 '1024-2047': 0, '2048-infinite': 0}
    total = 0
    for tuple in cursor.fetchall():
        length = int(tuple[0])
        count =  int(tuple[1])
        total += count
        if length < 128:
            intervals['0-127'] += count
        elif length < 256:
            intervals['128-255'] += count
        elif length < 512:
            intervals['256-511'] += count
        elif length < 1024:
            intervals['512-1023'] += count
        elif length < 2048:
            intervals['1024-2047'] += count
        else:
            intervals['2048-infinite'] += count
    sys.stdout.write ("%2.6f %2.6f %2.6f %2.6f %2.6f %2.6f" %  \
                          (float(intervals['0-127'])/total, 
                           float(intervals['128-255'])/total, 
                           float(intervals['256-511'])/total, 
                           float(intervals['512-1023'])/total, 
                           float(intervals['1024-2047'])/total, 
                           float(intervals['2048-infinite'])/total))
    sys.stdout.write ("\n")
conn.close()
