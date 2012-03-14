#!/usr/bin/python
# -*- coding: utf-8 -*-

from simpletal import simpleTAL, simpleTALES, simpleTALUtils
import psycopg2
import locale
import time

encoding = "UTF-8"
sniffer = "jezabel"

known_asn = {16276: 'OVH', 8560: '1&1', 29169: 'Gandi', 12322: 'Free', 13034: 'Pages jaunes', 39729: 'Register.IT', 8362: 'NordNet', 13193: 'Nerim', 12670: 'Completel', 3215: 'Orange', 15169: 'Google', 47846: 'Sedo GmbH'}

def asn_owner(asn):
    try:
        return known_asn[asn]
    except Exception:
        return ''


conn = psycopg2.connect("dbname=dnsdelve-redirections")
cursor = conn.cursor()

html_page = open("redirections.tmpl.xhtml")
template = simpleTAL.compileXMLTemplate(html_page)
context = simpleTALES.Context()

locale.setlocale(locale.LC_NUMERIC, "fr_FR.%s" % encoding)
locale.setlocale(locale.LC_TIME, "fr_FR.%s" % encoding)

cursor.execute("SELECT uuid, date FROM runs ORDER BY date DESC LIMIT 1")
(uuid, date) = cursor.fetchone()
date = unicode(date.strftime("%d %B %Y à %H:%M"), encoding)

# All checked domains
cursor.execute("SELECT count(target) FROM Redirect WHERE uuid = %(uuid)s""", {'uuid': uuid})
total = int(cursor.fetchone()[0])

# All redirected domains
cursor.execute("""SELECT count(r.target) FROM Redirect r
WHERE r.orig != r.target AND uuid = %(uuid)s""", {'uuid': uuid})
total_visible_redirections = float(cursor.fetchone()[0])
redirections_ratio = "%2.2f" % (total_visible_redirections*100.0/total)

# All self-redirected domains (to a specific page or a subdomain...)
cursor.execute("""SELECT count(r.target) FROM Redirect r
INNER JOIN uri o ON r.orig = o.id
INNER JOIN uri t ON r.target = t.id
WHERE o.reg_dom = t.reg_dom
AND r.orig != r.target
AND uuid = %(uuid)s""", {'uuid': uuid})
self_redirections = ("%2.2f" % (float(cursor.fetchone()[0]*100.0/total_visible_redirections)))

# All redirected domains (to another domain)
cursor.execute("""SELECT count(r.target) FROM Redirect r
INNER JOIN uri o ON r.orig = o.id
INNER JOIN uri t ON r.target = t.id
WHERE o.reg_dom != t.reg_dom
AND uuid = %(uuid)s""", {'uuid': uuid})
out_redirections = float(cursor.fetchone()[0])

# All (considered) bad redirections 
cursor.execute("""SELECT count(*) FROM Redirect r
INNER JOIN uri o ON r.orig = o.id
INNER JOIN uri t ON r.target = t.id
WHERE t.uri = 'Bad redirection' AND r.uuid = %(uuid)s""", {'uuid': uuid})
bad_redirections = ("%2.2f" % (float(cursor.fetchone()[0]*100.0/total)))

# Top redirections types
cursor.execute("""SELECT type, count(*) AS total FROM Crossed_redirections c
INNER JOIN Redirect r ON c.id_redirect = r.id
WHERE c.type != 'CNAME'
AND r.uuid = %(uuid)s
GROUP BY c.type ORDER BY total DESC""", {'uuid': uuid})
redirections_type = []
total_crossed_redirections = 0.0
for tuple in cursor.fetchall():
    total_crossed_redirections += float(tuple[1])
    redirections_type.append({'type': tuple[0], 'count': float(tuple[1])})
for r in redirections_type:
    r['count'] = "%2.2f" % (r['count']*100.0/total_crossed_redirections)

# Top TLD for redirections
cursor.execute("""SELECT t.tld AS ttld, count(t.tld) AS total FROM Redirect r
INNER JOIN uri o ON r.orig = o.id
INNER JOIN uri t ON r.target = t.id
WHERE o.reg_dom != t.reg_dom
AND r.uuid = %(uuid)s
GROUP BY ttld ORDER BY total DESC LIMIT 20;""", {'uuid': uuid})
redirections_tld = []
for tuple in cursor.fetchall():
    redirections_tld.append({'tld': tuple[0], 'count': ("%2.2f" % (float(tuple[1])*100.0/out_redirections))})

# Top hostname for redirections
cursor.execute("""SELECT t.authority AS domain, count(*) AS total FROM Redirect r
INNER JOIN uri o ON r.orig = o.id
INNER JOIN uri t ON r.target = t.id
WHERE o.reg_dom != t.reg_dom
AND t.uri != 'Bad redirection' 
AND r.uuid = %(uuid)s
GROUP BY domain ORDER BY total DESC LIMIT 5""", {'uuid': uuid})
redirections_auth = []
for tuple in cursor.fetchall():
    redirections_auth.append({'auth': tuple[0], 'count': ("%2.2f" % (float(tuple[1])*100.0/out_redirections))})

# Number of time an AS was crossed
cursor.execute("""SELECT count(*) FROM ASN a
INNER JOIN URI t ON a.authority = t.authority
INNER JOIN Crossed_redirections c ON c.target = t.id
INNER JOIN URI o ON o.id = c.origin
INNER JOIN Redirect r ON r.id = c.id_redirect
WHERE o.authority != t.authority
AND a.uuid = %(uuid)s AND r.uuid = %(uuid)s""", {'uuid': uuid})
total_asn = int(cursor.fetchone()[0])

# Top crossed AS
cursor.execute("""SELECT a.asn, count(*) AS total FROM ASN a
INNER JOIN URI t ON a.authority = t.authority
INNER JOIN Crossed_redirections c ON c.target = t.id
INNER JOIN URI o ON o.id = c.origin
INNER JOIN Redirect r ON r.id = c.id_redirect
WHERE o.authority != t.authority
AND a.uuid = %(uuid)s AND r.uuid = %(uuid)s
GROUP BY a.asn ORDER BY total DESC LIMIT 5""", {'uuid': uuid})
redirections_asn = []
for tuple in cursor.fetchall():
    redirections_asn.append({'asn': tuple[0], 'owner': asn_owner(tuple[0]), 'count': ("%2.2f" % (float(tuple[1])*100.0/total_asn))})

context.addGlobal("now", date)
context.addGlobal("redirections_count", redirections_ratio)
context.addGlobal("redirections_tld", redirections_tld)
context.addGlobal("redirections_auth", redirections_auth)
context.addGlobal("redirections_asn", redirections_asn)
context.addGlobal("self_redirections", self_redirections)
context.addGlobal("bad_redirections", bad_redirections)
context.addGlobal("redirections_type", redirections_type)

rendered = simpleTALUtils.FastStringOutput()
template.expand (context, rendered, outputEncoding=encoding)
output = open("redirections.html", 'w')
output.write(rendered.getvalue())
output.write("\n")
output.close()

conn.commit()
conn.close()

