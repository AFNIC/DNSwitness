#!/usr/bin/python

""" DNSdelve module to detect DNSSEC use by checking the DNSKEY record. """

# Standard modules
import Queue
import random
import getopt
import sys
import time
import struct

# www.dnspython.org
import dns.resolver

# Local
import BaseResult
import BasePlugin
import Utils

# Default settings 
database = "dbname=dnssec"
num_writing_tasks = 10
write_delay = 2 # seconds
# TODO: the timeout of queries?

# Global
writers = []
zonefilename = None
samplingrate = None

def module_usage(msg=None):
    print >>sys.stderr, "Usage of this Dnssec module: [-b database_name] [-r resolvers_addresses] [-n N] "
    if msg is not None:
        print >>sys.stderr, msg

class DnssecResult(BaseResult.Result):

    def __init__(self):
        self.zone_broken = None
        self.dnskey = None
        self.nsec = None
        self.domain = None
        self.keys = None
        BaseResult.Result.__init__(self)

    def __str__(self):
        return "%s\n%s" % (self.dnskey, self.nsec)

    def store(self, uuid):
        if self.dnskey is not None:
            has_dnskey = True
        else:
            has_dnskey = False
        if self.nsec is not None:
            has_nsec = True
        else:
            has_nsec = False
        dbw_command = ["tests", {"uuid": str(uuid), "domain":self.domain,
                                 "broken":self.zone_broken,
                                 "dnskey": has_dnskey, "nsec": has_nsec}]

        if self.keys is not None:
            for key in self.keys:
                dbw_command.append("DBW_CALL_SQL_FUNCTION")
                dbw_command.append("insert_dnssec")
                dbw_command.append([str(uuid), self.domain, key['key_id'],
                          key['algorithm'], key['key_length'],
                          key['key']])
        self.writer.channel.put(dbw_command)


class Plugin(BasePlugin.Plugin):

    def query(self, zone, nameservers):
        global writers
        zone_broken = False
        nsec_result = None
        dnskey_result = None
        algorithm = None
        key_len = None
        try:
            dnskey_result = myresolver.query (zone, 'DNSKEY')
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            dnskey_result = None
        except (dns.resolver.NoNameservers, dns.resolver.Timeout):
            # No second chance: the zone is broken, we never try again
            dnskey_result = None
            zone_broken = True
        if not zone_broken:
            try:
                # The presence of a DNSKEY record does not mean the
                # zone is signed. So, we test also other records.
                # TODO: RRSIG always raise NoAnswer. Probably a bug in
                # dns-python (see for instance
                # <http://stackoverflow.com/questions/82607/python-dns-cannot-get-rrsig-records-no-answer>). So,
                # we query NSEC and NSEC3.
                try:
                    nsec_result = myresolver.query (zone, 'NSEC')
                except dns.resolver.NoAnswer:
                    nsec_result = myresolver.query (zone, 50) # Resource record type 50 is NSEC3,
                    # not yet known by dnspython
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                nsec_result = None
            except (dns.resolver.NoNameservers, dns.resolver.Timeout):
                nsec_result = None
                zone_broken = True
        fullresult = DnssecResult()
        fullresult.zone_broken = zone_broken
        fullresult.dnskey = dnskey_result
        fullresult.nsec = nsec_result
        fullresult.domain = zone
        fullresult.writer = random.choice(writers)

        if dnskey_result is not None:
            fullresult.keys = []
            for k in dnskey_result:
                key = {}
                # Compute the key size
                # Mostly a copy-paste from the "_validate_rrsig()" function
                # (dns/dnssec.py in dnspython)
                # See also RFC 3110, 2. RSA Public KEY Resource Records
                if dns.dnssec._is_rsa(k.algorithm):
                    keyptr = k.key
                    (bytes,) = struct.unpack('!B', keyptr[0:1])
                    keyptr = keyptr[1:]
                    if bytes == 0:
                        (bytes,) = struct.unpack('!H', keyptr[0:2])
                        keyptr = keyptr[2:]
                    rsa_n = keyptr[bytes:]
                    key['key_length'] = len(rsa_n) * 8
                else:
                    # TODO Compute the key size for other algorithms (DSA, GOST...)
                    key['key_length'] = None
                key['algorithm'] = k.algorithm
                key['key_id'] = dns.dnssec.key_id(k)
                key['key'] = dns.rdata._base64ify(k.key)
                fullresult.keys.append(key)
        return fullresult

def config(args, zonefile, sampling):
    global database, num_writing_tasks, resolvers, zonefilename, samplingrate
    try:
        resolvers = None
        optlist, args = getopt.getopt (args, "hn:b:r:",
                                       ["help", "num_tasks=", "database=", 
                                        "resolvers="])
        for option, value in optlist:
            if option == "--help" or option == "-h":
                module_usage()
                sys.exit(0)
            elif option == "--num_tasks" or option == "-n":
                num_writing_tasks = int(value)
            elif option == "--database" or option == "-b":
                database = value
                if database.find('=') == -1:
                    # User only indicated the database name, let's make a proper conninfo
                    database="dbname=%s" % database
            elif option == "--resolvers" or option == "-r":
                resolvers = value.split(',')
            else:
                # Should never occur, it is trapped by getopt
                module_usage("Internal error: unhandled option %s" % option)
                sys.exit(1)
    except getopt.error, reason:
        module_usage(reason)
        sys.exit(1)
    if len(args) != 0:
        module_usage("Remaining arguments: %s" % args)
        sys.exit(1)
    zonefilename = zonefile
    samplingrate = sampling

def start(uuid, all_domains):
    global database, writers, myresolver, resolvers, num_writing_tasks
    myresolver = Utils.make_resolver(resolvers, 4096)
    Utils.write_domains(database, uuid, all_domains)
    Utils.write_run(database, uuid, "Dnssec", zonefilename, len(all_domains), None, samplingrate)
    writers = []
    for writer in range(1, num_writing_tasks+1):
        channel = Queue.Queue()
        writers.append(Utils.DatabaseWriter(writer, database, channel))
        writers[writer-1].start()

def final():
    global writers, write_delay
    time.sleep(write_delay) # Let the queries put the final data in the queues
    for writer in range(1, num_writing_tasks+1):
        writers[writer-1].channel.put([None, None])
    for writer in range(1, num_writing_tasks+1):
        writers[writer-1].join()

if __name__ == '__main__':
    raise Exception("Not yet usable as a main program, sorry")

