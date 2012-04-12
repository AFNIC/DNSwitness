#!/usr/bin/python
# -*- coding: utf-8 -*-

from simpletal import simpleTAL, simpleTALES, simpleTALUtils
import psycopg2
import locale
import time
import Utils

encoding = "UTF-8"
sniffer = "lilith"
num_probes = 3

conn = psycopg2.connect("dbname=dnsmezzo")
cursor = conn.cursor()

html_page = open("ipv6.tmpl.xhtml")
template = simpleTAL.compileXMLTemplate(html_page)
context = simpleTALES.Context()

# TODO: ignored, decimal numbers are formatted with a dot :-(
locale.setlocale(locale.LC_NUMERIC, "fr_FR.%s" % encoding)
# But month names are OK
locale.setlocale(locale.LC_TIME, "fr_FR.%s" % encoding)

filter = ""
for (id, last_date) in Utils.get_set_days(cursor, sniffer, limit=num_probes*2):
    if filter == "":
        filter = "file=%i" % id
    else:
        filter += " OR file=%i" % id
cursor.execute("SELECT count(id) FROM DNS_packets WHERE query AND (%s);" % filter)
total_queries = int(cursor.fetchone()[0])
cursor.execute("SELECT count(id) FROM DNS_packets WHERE query AND family(src_address)=6 AND (%s);" % \
                   filter)
context.addGlobal("v6-queries", "%2.1f" % ((float(cursor.fetchone()[0])*100)/total_queries))

rendered = simpleTALUtils.FastStringOutput()
template.expand (context, rendered, outputEncoding=encoding)
output = open("ipv6.html", 'w')
output.write(rendered.getvalue())
output.write("\n")
output.close()

conn.close()
