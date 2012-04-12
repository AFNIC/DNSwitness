#!/usr/bin/python
# -*- coding: utf-8 -*-

import psycopg2
import locale
import time
import Utils

encoding = "UTF-8"
sniffer = "lilith"

conn = psycopg2.connect("dbname=dnsmezzo")
cursor = conn.cursor()
cursor_int = conn.cursor()
num_probes = 3
num_files = num_probes * 2 * 10

# TODO: ignored, decimal numbers are formatted with a dot :-(
locale.setlocale(locale.LC_NUMERIC, "fr_FR.%s" % encoding)

for (last_id, last_date) in Utils.get_set_days(cursor_int, sniffer, limit=num_files):
    # TODO: validity control, that the id exists and that there is < 10 days between the dates
    cursor.execute("SELECT count(id) FROM DNS_packets WHERE query AND file=%(id)s;", 
                   {'id': last_id})
    total_queries = int(cursor.fetchone()[0])
    if total_queries == 0:
        continue
    cursor.execute("SELECT count(id) FROM DNS_packets WHERE query AND family(src_address)=4 AND file=%(id)s;", 
                   {'id': last_id})
    v4_queries = int(cursor.fetchone()[0])
    cursor.execute("SELECT count(id) FROM DNS_packets WHERE query AND family(src_address)=6 AND file=%(id)s;", 
                   {'id': last_id})
    v6_queries = int(cursor.fetchone()[0])
    print "%s %2.2f %2.2f" % \
        (last_date.strftime("%d/%m/%Y"), 
                                    float(v4_queries*100)/total_queries, float(v6_queries*100)/total_queries)

conn.close()
