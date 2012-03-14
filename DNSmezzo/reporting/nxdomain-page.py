#!/usr/bin/python
# -*- coding: utf-8 -*-

from simpletal import simpleTAL, simpleTALES, simpleTALUtils
import psycopg2
import locale
import time
import Utils

encoding = "UTF-8"
sniffer = "jezabel"
limit = 100

conn = psycopg2.connect("dbname=dnsmezzo3")
cursor = conn.cursor()

html_page = open("nxdomain.tmpl.xhtml")
template = simpleTAL.compileXMLTemplate(html_page)
context = simpleTALES.Context()

# TODO: ignored, decimal numbers are formatted with a dot :-(
locale.setlocale(locale.LC_NUMERIC, "fr_FR.%s" % encoding)
# But month names are OK
locale.setlocale(locale.LC_TIME, "fr_FR.%s" % encoding)

(last_sunday_id, last_tuesday_id, last_tuesday_date) = Utils.get_set_days(cursor, sniffer, 1).next()
cursor.execute("SELECT DISTINCT registered_domain AS domain, count(registered_domain) AS num FROM DNS_packets WHERE (file=%(sunday)s OR file=%(tuesday)s) AND NOT query AND rcode=3 GROUP BY registered_domain ORDER BY num DESC LIMIT %(limit)s", 
                   {'sunday': last_sunday_id, 'tuesday': last_tuesday_id, 'limit': limit})
domains = []
for (domain, count) in cursor.fetchall():
    domains.append({'domain': unicode(domain, "latin-1"), 'count': count})
context.addGlobal ("domains", domains)

now = time.localtime(time.time())
now_str = time.strftime("%d %B %Y à %H:%M", now)
context.addGlobal("now", unicode(now_str, encoding))

rendered = simpleTALUtils.FastStringOutput()
template.expand (context, rendered, outputEncoding=encoding)
output = open("nxdomain.html", 'w')
output.write(rendered.getvalue())
output.write("\n")
output.close()

conn.close()
