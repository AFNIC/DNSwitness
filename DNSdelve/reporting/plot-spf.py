#!/usr/bin/python
# -*- coding: utf-8 -*-

import psycopg2
import locale
import time
import Utils

encoding = "UTF-8"

conn = psycopg2.connect("dbname=dnswitness-spf")
cursor = conn.cursor()
cursor_int = conn.cursor()

# TODO: ignored, decimal numbers are formatted with a dot :-(
locale.setlocale(locale.LC_NUMERIC, "fr_FR.%s" % encoding)

cursor.execute("SELECT uuid,date,samplingrate FROM Runs ORDER BY date ASC;")
for tuple in cursor.fetchall():
    uuid = tuple[0]
    date = tuple[1]
    sampling_rate = tuple[2]
    cursor_int.execute("SELECT count(domain) FROM Tests WHERE uuid=%(uuid)s;",
               {'uuid': uuid})
    total_domains = int(cursor_int.fetchone()[0])
    cursor_int.execute("SELECT count(domain) FROM Tests WHERE spf IS NOT NULL AND uuid=%(uuid)s;",
               {'uuid': uuid})
    enabled_domains = int(cursor_int.fetchone()[0])
    enabled_proportion = float(enabled_domains)/total_domains
    if sampling_rate is not None:
        sampling_rate = float(sampling_rate)
        sample_size = total_domains
        enabled_error = Utils.find_err(sample_size, total_domains/sampling_rate, 
                               enabled_proportion)
    else: # Historic data, sampling rate unknown
        enabled_error = 0.0
    print "%s %2.0f %2.3f" % (date.strftime("%d/%m/%Y"), 
                     enabled_proportion*100, enabled_error)

conn.close()
