#!/usr/bin/python

""" Finds out the UUID of the first reports before and after a given date """

import sys
import time
import psycopg2

if len(sys.argv) != 3:
    print >>sys.stderr, "Usage: %s date dbinfo" % sys.argv[0]
    sys.exit(1)

date_str = sys.argv[1]
dbinfo = sys.argv[2]

try:
    dbinfo.index("dbname=")
except ValueError:
    dbinfo = "dbname=%s" % dbinfo

try:
    date = time.strptime(date_str, "%Y-%m-%d")
    date_sql = time.strftime("%Y-%m-%d", date)
except ValueError:
    print >>sys.stderr, "Wrong date format %s" % date_str
    sys.exit(1)

conn = psycopg2.connect(dbinfo)
cursor = conn.cursor()
cursor.execute("""
   SELECT uuid, date FROM Runs WHERE date > '%s' ORDER BY date LIMIT 1""" % date_sql);
after = cursor.fetchone()[0]
cursor.execute("""
   SELECT uuid, date FROM Runs WHERE date < '%s' ORDER BY date DESC LIMIT 1""" % date_sql);
before = cursor.fetchone()[0]
cursor.close()
conn.close()
print """
        WHERE uuid = '%s'
           AND 
            address NOT IN (SELECT address FROM Hosts 
                            WHERE uuid = '%s')
""" % (after, before)
