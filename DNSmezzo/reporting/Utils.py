#!/usr/bin/python

def get_set_days(cursor, host, reverse=True, limit=100):
    last_sunday_id = None
    last_tuesday_id = None
    if reverse:
        order = "DESC"
    else:
        order = ""
    cursor.execute("SELECT id, date_part('dow', lastpacket), lastpacket, samplingrate, storedpackets FROM pcap_files WHERE hostname = '%s' ORDER BY added %s LIMIT %i;" % (host, order, limit*5))
    for tuple in cursor.fetchall():
        id = tuple[0]
        dow = tuple[1]
        date = tuple[2]
        sampling_rate = tuple[3]
        if dow == 0 and last_sunday_id is None:
            last_sunday_id = id
            last_sunday_date = date
            if last_tuesday_id is not None:
                yield (last_sunday_id, last_tuesday_id, last_tuesday_date)
                last_sunday_id = None
                last_tuesday_id = None
        if dow == 2 and last_tuesday_id is None:
            last_tuesday_id = id
            last_tuesday_date = date
            if last_sunday_id is not None:
                yield (last_sunday_id, last_tuesday_id, last_tuesday_date)
                last_sunday_id = None
                last_tuesday_id = None


