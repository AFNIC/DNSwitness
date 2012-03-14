#!/usr/bin/python
# -*- coding: utf-8 -*-

from simpletal import simpleTAL, simpleTALES, simpleTALUtils
import psycopg2
import locale
import time

import Utils

encoding = "UTF-8"

known_algorithm = {1:'RSA/MD5', 2:'Diffie-Hellman', 3:'DSA/SHA1', 5:'RSA/SHA1', 6:'DSA-NSEC3-SHA1', 7:'RSASHA1-NSEC3-SHA1', 8:'RSA/SHA-256', 10:'RSA/SHA-512', 12:'GOST R 34.10-2001'}

def algorithm(number):
    try:
        return known_algorithm[number]
    except Exception:
        return ''

conn = psycopg2.connect("dbname=dnswitness-dnssec")
cursor = conn.cursor()

html_page = open("dnssec.tmpl.xhtml")
template = simpleTAL.compileXMLTemplate(html_page)
context = simpleTALES.Context()

# TODO: ignored, decimal numbers are formatted with a dot :-(
locale.setlocale(locale.LC_NUMERIC, "fr_FR.%s" % encoding)
# But month names are OK
locale.setlocale(locale.LC_TIME, "fr_FR.%s" % encoding)

(context, last_uuid, last_num_domains, last_sampling) = Utils.basic_facts(cursor, 
                                                                          encoding, context)
cursor.execute("SELECT count(domain) FROM Tests WHERE dnskey AND nsec AND uuid=%(last_uuid)s;",
               {'last_uuid': last_uuid})
last_enabled = int(cursor.fetchone()[0])

cursor.execute("""SELECT k.algorithm, count(*) AS total FROM keys k
JOIN tests_keys tk ON k.id = tk.id_key
JOIN Tests t ON t.id = tk.id_test
WHERE uuid = %(last_uuid)s
GROUP BY k.algorithm ORDER BY total DESC""", {'last_uuid': last_uuid})
algorithm_stats = []
for tuple in cursor.fetchall():
    algorithm_stats.append({'number': tuple[0], 'description': algorithm(tuple[0]), 'count': tuple[1]})

context.addGlobal("last-enabled", "%i" % last_enabled)
context.addGlobal("last-enabled-permillionage", "%2.6f" % (float(last_enabled*1000000)/last_num_domains))
context.addGlobal("algorithm", algorithm_stats)

rendered = simpleTALUtils.FastStringOutput()
template.expand (context, rendered, outputEncoding=encoding)
output = open("dnssec.html", 'w')
output.write(rendered.getvalue())
output.write("\n")
output.close()

conn.close()
