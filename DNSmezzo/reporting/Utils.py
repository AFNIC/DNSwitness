#!/usr/bin/python

def get_set_days(cursor, host, reverse=True, limit=10):
    last_date = None
    if reverse:
        order = "DESC"
    else:
        order = ""
    filter = ""
    cursor.execute("SELECT id, date_part('dow', lastpacket), lastpacket, samplingrate, storedpackets FROM pcap_files WHERE hostname = '%s' ORDER BY added %s LIMIT %i;" % (host, order, limit))
    for tuple in cursor.fetchall():
        id = tuple[0]
        dow = tuple[1]
        date = tuple[2]
        sampling_rate = tuple[3]
        if last_date is None:
            last_date = date
        yield (id, last_date)
        last_date = None

