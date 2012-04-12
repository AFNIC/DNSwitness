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
limit_domains = 100

conn = psycopg2.connect("dbname=dnsmezzo")
cursor = conn.cursor()

html_page = open("top100.tmpl.xhtml")
template = simpleTAL.compileXMLTemplate(html_page)
context = simpleTALES.Context()

# TODO: ignored, decimal numbers are formatted with a dot :-(
locale.setlocale(locale.LC_NUMERIC, "fr_FR.%s" % encoding)
# But month names are OK
locale.setlocale(locale.LC_TIME, "fr_FR.%s" % encoding)

filter = ""
for (id, last_date) in Utils.get_set_days(cursor, sniffer, limit=num_probes*2*5):
    if filter == "":
        filter = "file=%i" % id
    else:
        filter += " OR file=%i" % id

cursor.execute("SELECT count(id) FROM DNS_packets WHERE query AND %s;" % filter)
total_queries = float(cursor.fetchone()[0])

cursor.execute("SELECT DISTINCT registered_domain AS domain, count(registered_domain) AS num FROM DNS_packets WHERE %s AND query GROUP BY registered_domain ORDER BY num DESC LIMIT %i" % (filter, limit_domains))
domains = []
for (domain, count) in cursor.fetchall():
    domains.append({'domain': unicode(domain, "latin-1"), 'count': (count*100/total_queries)})
context.addGlobal ("domains", domains)

now = time.localtime(time.time())
now_str = time.strftime("%d %B %Y à %H:%M", now)
context.addGlobal("now", unicode(now_str, encoding))

rendered = simpleTALUtils.FastStringOutput()
template.expand (context, rendered, outputEncoding=encoding)
output = open("top100.html", 'w')
output.write(rendered.getvalue())
output.write("\n")
output.close()

conn.close()
