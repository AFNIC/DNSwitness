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
cursor_int = conn.cursor()

# TODO: ignored, decimal numbers are formatted with a dot :-(
locale.setlocale(locale.LC_NUMERIC, "fr_FR.%s" % encoding)

for (last_sunday_id, last_tuesday_id, last_tuesday_date) in Utils.get_set_days(cursor, sniffer):
    # TODO: validity control, that the id exists and that there is < 10 days between the dates
    cursor.execute("SELECT count(id) FROM DNS_packets WHERE query AND (file=%(sunday)s OR file=%(tuesday)s);", 
                   {'sunday': last_sunday_id, 'tuesday': last_tuesday_id})
    total_queries = int(cursor.fetchone()[0])
    cursor.execute("SELECT count(id) FROM DNS_packets WHERE query AND family(src_address)=4 AND (file=%(sunday)s OR file=%(tuesday)s);", 
                   {'sunday': last_sunday_id, 'tuesday': last_tuesday_id})
    v4_queries = int(cursor.fetchone()[0])
    cursor.execute("SELECT count(id) FROM DNS_packets WHERE query AND family(src_address)=6 AND (file=%(sunday)s OR file=%(tuesday)s);", 
                   {'sunday': last_sunday_id, 'tuesday': last_tuesday_id})
    v6_queries = int(cursor.fetchone()[0])
    print "%s %2.2f %2.2f" % \
        (last_tuesday_date.strftime("%d/%m/%Y"), 
                                    float(v4_queries*100)/total_queries, float(v6_queries*100)/total_queries)

conn.close()
