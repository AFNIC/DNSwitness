#!/usr/bin/python
# -*- coding: utf-8 -*-

from simpletal import simpleTAL, simpleTALES, simpleTALUtils
import psycopg2
import locale
import time

encoding = "UTF-8"

conn = psycopg2.connect("dbname=dnsdelve-ip")
cursor = conn.cursor()

html_page = open("ipv6.tmpl.xhtml")
template = simpleTAL.compileXMLTemplate(html_page)
context = simpleTALES.Context()

# TODO: ignored, decimal numbers are formatted with a dot :-(
locale.setlocale(locale.LC_NUMERIC, "fr_FR.%s" % encoding)
# But month names are OK
locale.setlocale(locale.LC_TIME, "fr_FR.%s" % encoding)

last_uuid = None
first_uuid = None
num_exec = 0
cursor.execute("SELECT uuid,date,samplingrate FROM Runs ORDER BY date DESC;")
for tuple in cursor.fetchall():
    num_exec += 1
    if last_uuid is None:
        # TODO: create a cache of answers, Cache.Counts and use it
        cursor.execute("SELECT count(*) FROM Broker WHERE uuid=%(last_uuid)s;",
               {'last_uuid': tuple[0]})
        last_num_domains = int(cursor.fetchone()[0])
        if last_num_domains == 0: # This run is not over, skip it
            # TODO: not perfect since part of the run may have been committed
            pass
        else:
            last_uuid = tuple[0]
            last_exec = tuple[1]
            last_sampling = float(tuple[2])
first_uuid = tuple[0]
first_exec = tuple[1]
cursor.execute("SELECT count(*) FROM V6_enabled WHERE uuid=%(last_uuid)s;",
               {'last_uuid': last_uuid})
last_enabled = int(cursor.fetchone()[0])
cursor.execute("SELECT count(*) FROM V6_full WHERE uuid=%(last_uuid)s;",
               {'last_uuid': last_uuid})
last_full = int(cursor.fetchone()[0])
context.addGlobal("last-enabled", "%2.1f" % (float(last_enabled*100)/last_num_domains))
context.addGlobal("last-full", "%2.3f" % (float(last_full*100)/last_num_domains))
context.addGlobal("last-num-domains", last_num_domains)
context.addGlobal("last-sampling", "%i" % int(last_sampling*100))
context.addGlobal("last-exec", unicode(last_exec.strftime("%d %B %Y à %H:%M"), encoding))
context.addGlobal("first-exec", unicode(first_exec.strftime("%d %B %Y à %H:%M"), encoding))
context.addGlobal("num-exec", num_exec)

# TODO: number of distinct addresses, of 6to4 or other funny
# addresses, test of wether it works or not, separate, SMTP, HTTP and
# DNS...

rendered = simpleTALUtils.FastStringOutput()
template.expand (context, rendered, outputEncoding=encoding)
output = open("ipv6.html", 'w')
output.write(rendered.getvalue())
output.write("\n")
output.close()

conn.close()
