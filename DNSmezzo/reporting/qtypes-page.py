#!/usr/bin/python
# -*- coding: utf-8 -*-

from simpletal import simpleTAL, simpleTALES, simpleTALUtils
import psycopg2
import locale
import time
import Utils

encoding = "UTF-8"
sniffer = "lilith"

conn = psycopg2.connect("dbname=dnsmezzo")
cursor = conn.cursor()

html_page = open("qtypes.tmpl.xhtml")
template = simpleTAL.compileXMLTemplate(html_page)
context = simpleTALES.Context()

# TODO: ignored, decimal numbers are formatted with a dot :-(
locale.setlocale(locale.LC_NUMERIC, "fr_FR.%s" % encoding)
# But month names are OK
locale.setlocale(locale.LC_TIME, "fr_FR.%s" % encoding)

(last_id, last_tuesday_date) = Utils.get_set_days(cursor, sniffer, 1).next()
cursor.execute("SELECT count(id) FROM DNS_packets WHERE query AND file=%(last_id)s;", 
                   {'last_id': last_id})
total_queries = int(cursor.fetchone()[0])
cursor.execute("""SELECT (CASE WHEN type IS NULL THEN qtype::TEXT ELSE type END), 
       meaning, 
       count(results.id) AS requests FROM 
             (SELECT id, qtype FROM dns_packets 
                  WHERE file=%(last_id)s AND query) AS Results
          LEFT OUTER JOIN DNS_types ON qtype = value
              GROUP BY qtype, type, meaning ORDER BY requests desc;""", 
               {'last_id': last_id})
qtypes_results = []
for tuple in cursor.fetchall():
    qtypes_results.append({'type': tuple[0], 'meaning': tuple[1], 
                           'count': ("%2.2f" % (float(tuple[2])*100/total_queries))})

now = time.localtime(time.time())
now_str = time.strftime("%d %B %Y à %H:%M", now)
context.addGlobal("now", unicode(now_str, encoding))

context.addGlobal("qtypes", qtypes_results)

rendered = simpleTALUtils.FastStringOutput()
template.expand (context, rendered, outputEncoding=encoding)
output = open("qtypes.html", 'w')
output.write(rendered.getvalue())
output.write("\n")
output.close()

conn.close()
