#!/usr/bin/python
# -*- coding: utf-8 -*-

import math

confidence = 1.959964; # 95 % confidence

def basic_facts(cursor, encoding, context):
    last_uuid = None
    first_uuid = None
    num_exec = 0
    cursor.execute("SELECT uuid,date,samplingrate FROM Runs ORDER BY date DESC;")
    for tuple in cursor.fetchall():
        num_exec += 1
        if last_uuid is None:
            last_uuid = tuple[0]
            last_exec = tuple[1]
            last_sampling = float(tuple[2])
    first_uuid = tuple[0]
    first_exec = tuple[1]
    cursor.execute("SELECT count(domain) FROM Tests WHERE uuid=%(last_uuid)s;",
                   {'last_uuid': last_uuid})
    last_num_domains = int(cursor.fetchone()[0])
    context.addGlobal("last-num-domains", last_num_domains)
    context.addGlobal("last-sampling", "%i" % int(last_sampling*100))
    context.addGlobal("last-exec", unicode(last_exec.strftime("%d %B %Y à %H:%M"), encoding))
    context.addGlobal("first-exec", unicode(first_exec.strftime("%d %B %Y à %H:%M"), encoding))
    context.addGlobal("num-exec", num_exec)
    return (context, last_uuid, last_num_domains, last_sampling)

def find_err(sample_size, pop_size, proportion):
    # http://www.nss.gov.au/nss/home.NSF/pages/Sample+size+calculator?OpenDocument
    f = float(sample_size-1)/float(pop_size-1)
    error = math.sqrt(((1-f)*(proportion*(1-proportion)))/(sample_size-1))
    return error
