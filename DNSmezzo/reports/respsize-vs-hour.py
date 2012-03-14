#!/usr/bin/python
# -*- coding: utf-8 -*-

import psycopg2
import locale
import time
import sys

encoding = "UTF-8"
sniffer = "jezabel"
file = 25
datestart = "2010-09-14"

conn = psycopg2.connect("dbname=dnsmezzo-tmp")
cursor = conn.cursor()
cursor_int = conn.cursor()

# TODO: ignored, decimal numbers are formatted with a dot :-(
locale.setlocale(locale.LC_NUMERIC, "fr_FR.%s" % encoding)

for hour in range(0,23):
    timemin = "%i:00:00" % hour
    timemax = "%i:59:59" % hour
    datemin = "%s %s" % (datestart, timemin)
    datemax = "%s %s" % (datestart, timemax)
    cursor.execute("SELECT avg(length) FROM dns_packets where file=%(file)s AND not query AND date <= %(datemax)s AND date >= %(datemin)s;", 
                   {'file': file, 'datemax': datemax, 'datemin': datemin})
    tuple = cursor.fetchone()
    if tuple[0] is None:
        length = 0
    else:
        length = int(tuple[0])
    sys.stdout.write ("%s %2.6f" %  \
                          (timemin, length))
    sys.stdout.write ("\n")
conn.close()
