#!/usr/bin/python
# -*- coding: utf-8 -*-

import psycopg2
import locale
import time

encoding = "UTF-8"
sniffer = "jezabel"

interesting_tld = ['net', 'com', 'fr', 'org', 'eu', 'de', 'info', 'be']

conn = psycopg2.connect("dbname=dnsdelve-redirections")
cursor = conn.cursor()

cursor.execute("SELECT uuid, date FROM runs ORDER BY date ASC;")
data = cursor.fetchall()

for d in data:
    uuid = d[0]
    date = unicode(d[1].strftime("%d/%m/%Y"), encoding)

    line = date

    cursor.execute("""SELECT count(*) FROM Redirect r
    INNER JOIN uri o ON r.orig = o.id
    INNER JOIN uri t ON r.target = t.id
    WHERE o.reg_dom != t.reg_dom AND uuid = %(uuid)s""", {'uuid': uuid})
    total = int(cursor.fetchone()[0])

    cursor.execute("""SELECT t.tld AS ttld, count(t.tld) AS total FROM Redirect r
    INNER JOIN uri o ON r.orig = o.id
    INNER JOIN uri t ON r.target = t.id
    WHERE o.reg_dom != t.reg_dom
    AND r.uuid = %(uuid)s
    GROUP BY ttld ORDER BY total;""", {'uuid': uuid})

    values = {}
    for tuple in cursor.fetchall():
        tld = tuple[0]
        count = float(tuple[1])*100/total
        values[tld] = count

    for tld in interesting_tld:
        try:
            line += " %2.2f" % values[tld]
            del values[tld]
        except KeyError:
            line += " 0.0"
    others = 0.0
    for tld in values.keys():
        if tld not in interesting_tld:
            others += values[tld]
    line += " %2.2f" % others
    print line

conn.commit()
conn.close()

