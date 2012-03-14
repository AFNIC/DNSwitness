#!/usr/bin/python
# -*- coding: utf-8 -*-

import psycopg2
import locale
import time
import Utils

encoding = "UTF-8"

conn = psycopg2.connect("dbname=dnsdelve-ip")
cursor = conn.cursor()
cursor_int = conn.cursor()

# TODO: ignored, decimal numbers are formatted with a dot :-(
locale.setlocale(locale.LC_NUMERIC, "fr_FR.%s" % encoding)

cursor.execute("SELECT uuid,date,samplingrate FROM Runs ORDER BY date ASC;")
for tuple in cursor.fetchall():
    uuid = tuple[0]
    date = tuple[1]
    sampling_rate = tuple[2]
    # TODO: create a cache of answers, Cache.Counts and use it
    cursor_int.execute("SELECT count(*) FROM Broker WHERE uuid=%(uuid)s;",
               {'uuid': uuid})
    total_domains = int(cursor_int.fetchone()[0])
    if total_domains == 0: # This run is not over, skip it
        # TODO: not perfect since part of the run may have been committed
        continue
    cursor_int.execute("SELECT count(*) FROM V6_enabled WHERE uuid=%(uuid)s;",
               {'uuid': uuid})
    v6_enabled_domains = int(cursor_int.fetchone()[0])
    cursor_int.execute("SELECT count(*) FROM V6_full WHERE uuid=%(uuid)s;",
               {'uuid': uuid})
    v6_full_domains = int(cursor_int.fetchone()[0])
    cursor_int.execute("SELECT count(*) FROM V6_web WHERE uuid=%(uuid)s;",
               {'uuid': uuid})
    v6_web_domains = int(cursor_int.fetchone()[0])
    cursor_int.execute("SELECT count(*) FROM V6_email WHERE uuid=%(uuid)s;",
               {'uuid': uuid})
    v6_email_domains = int(cursor_int.fetchone()[0])
    cursor_int.execute("SELECT count(*) FROM V6_dns WHERE uuid=%(uuid)s;",
               {'uuid': uuid})
    v6_dns_domains = int(cursor_int.fetchone()[0])
    if sampling_rate is not None:
        error_enabled = Utils.find_err(total_domains, total_domains/sampling_rate, 
                               float(v6_enabled_domains)/total_domains)
        error_full = Utils.find_err(total_domains, total_domains/sampling_rate, 
                               float(v6_full_domains)/total_domains)
        error_web = Utils.find_err(total_domains, total_domains/sampling_rate, 
                               float(v6_web_domains)/total_domains)
        error_email = Utils.find_err(total_domains, total_domains/sampling_rate, 
                               float(v6_email_domains)/total_domains)
        error_dns = Utils.find_err(total_domains, total_domains/sampling_rate, 
                               float(v6_dns_domains)/total_domains)
    else:
        error_enabled = 0
        error_full = 0
        error_web = 0
        error_email = 0
        error_dns = 0
    print "%s %4.2f %4.6f %4.2f %4.6f %4.2f %4.6f %4.2f %4.6f %4.2f %4.6f" % (date.strftime("%d/%m/%Y"), 
                     float(v6_enabled_domains*100)/total_domains, error_enabled,
                     float(v6_full_domains*100)/total_domains, error_full,
                     float(v6_web_domains*100)/total_domains, error_web,
                     float(v6_email_domains*100)/total_domains, error_email,
                     float(v6_dns_domains*100)/total_domains, error_dns)

conn.close()
