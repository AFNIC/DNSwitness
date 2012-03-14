#!/usr/bin/python

""" DNSdelve module to detect SPF use by checking the TXT and SPF
records and ADSP use by checking the _adsp._domainkey records."""

# Standard modules
import Queue
import random
import getopt
import sys
import time
import re

# www.dnspython.org
import dns.resolver

# Local
import BaseResult
import BasePlugin
import Utils

# Default settings 
database = "dbname=spf"
num_writing_tasks = 10
write_delay = 2 # seconds
# TODO: the timeout of queries?

# Global
writers = []
zonefilename = None
samplingrate = None

def module_usage(msg=None):
    print >>sys.stderr, "Usage of this Spf module: [-b database_name] [-r resolvers_addresses] [-n N] "
    if msg is not None:
        print >>sys.stderr, msg

class SpfResult(BaseResult.Result):
    
    def __init__(self):
        self.spf = None
        self.adsp = None
        BaseResult.Result.__init__(self)

    def __str__(self):
        return "SPF: %s, ADSP: %s" % (self.spf, self.adsp)

    def store(self, uuid):
        if self.spf is not None:
            first_record = self.spf[0] # Only one SPF record, in theory
            try: # Hack. TXT records can contain everything. We guess.
                spf_record = first_record.decode("utf-8")
            except UnicodeDecodeError:
                spf_record = first_record.decode("latin-1")
            has_spf = True
        else:
            spf_record = None
            has_spf = False
        if self.adsp is not None:
            record = self.adsp 
            try: # Hack. TXT records can contain everything. We guess.
                adsp_record = record.decode("utf-8")
            except UnicodeDecodeError:
                adsp_record = record.decode("latin-1")
            has_adsp = True
        else:
            adsp_record = None
            has_adsp = False
        self.writer.channel.put(["tests", {"uuid": str(uuid), "domain":self.domain,
                                 "broken":self.zone_broken,
                                 "spf": spf_record, "adsp": adsp_record}])
        
class Plugin(BasePlugin.Plugin):

    def query(self, zone, nameservers):
        global writers
        zone_broken = False
        spf_result = None
        try:
            spf_result = myresolver.query (zone, 'SPF')
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            spf_result = None
        except (dns.resolver.NoNameservers, dns.resolver.Timeout):
            # No second chance: the zone is broken, we never try again
            spf_result = None
            zone_broken = True
        if spf_result is None and not zone_broken:
            # As of 2008-09-22, most SPF zones still use the
            # original TXT record type, not the official SPF
            # record type.
            try:
                spf_result = myresolver.query (zone, 'TXT')
                final_result = []
                if spf_result is not None:
                    # Filter out other (non-SPF) TXT records
                    for record in spf_result.rrset.items:
                        try:
                            record_string = " ".join(record.strings)
                        except AttributeError:
                            # In some cases (for instance when the TXT
                            # record ends with a NUL character, like
                            # for sumantri.fr, there is no strings
                            # attribute.
                            continue # Ignore it
                        if not re.search("^v=spf1", record_string):
                            continue
                        final_result.append(record_string)
                    if len(final_result) != 0:
                        spf_result = final_result
                    else:
                        spf_result = None
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                spf_result = None
            except (dns.resolver.NoNameservers, dns.resolver.Timeout):
                nspf_result = None
                zone_broken = True
        elif spf_result is not None:
            spf_result = [" ".join(s.strings) for s in spf_result.rrset.items]
        if not zone_broken:
            # ADSP, DKIM Author Domain Signing Practices, Internet-Draft draft-ietf-dkim-ssp
            try:
                adsp_result = myresolver.query ("_adsp._domainkey.%s" % zone, 'TXT')
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                adsp_result = None
            except (dns.resolver.NoNameservers, dns.resolver.Timeout):
                adsp_result = None
                zone_broken = True
            if adsp_result is not None:
                for record in adsp_result.rrset.items:
                    record_string = " ".join(record.strings)
                    if not re.search("^dkim=", record_string): # Common, because of
                        # wildcards so you often find SPF records in
                        # _adsp._domainkey.domain.example :-(
                            adsp_result = None
                            record_string = ""
                            continue
                    else:
                        break # Stop at the first good one
                final_result = record_string
                if len(final_result) != 0:
                    adsp_result = final_result
                else:
                    adsp_result = None
        else:
            adsp_result = None
        fullresult = SpfResult()
        fullresult.zone_broken = zone_broken
        fullresult.spf = spf_result
        fullresult.adsp = adsp_result
        fullresult.domain = zone
        fullresult.writer = random.choice(writers)
        return fullresult

def config(args, zonefile, sampling):
    global database, num_writing_tasks, resolvers, zonefilename, samplingrate
    resolvers = None
    try:
        optlist, args = getopt.getopt (args, "hn:b:r:",
                                       ["help", "num_tasks=", "database=", 
                                        "resolvers="])
        for option, value in optlist:
            if option == "--help" or option == "-h":
                module_usage()
                sys.exit(0)
            elif option == "--num_tasks" or option == "-n":
                num_writing_tasks = int(value)
            elif option == "--resolvers" or option == "-r":
                resolvers = value.split(',')
            elif option == "--database" or option == "-b":
                database = value
                if database.find('=') == -1:
                    # User only indicated the database name, let's make a proper conninfo
                    database="dbname=%s" % database
            else:
                # Should never occur, it is trapped by getopt
                module_usage("Internal error: unhandled option %s" % option)
                sys.exit(1)
    except getopt.error, reason:
        module_usage(reason)
        sys.exit(1)
    if len(args) != 0:
        module_usage()
        sys.exit(1)
    zonefilename = zonefile
    samplingrate = sampling

def start(uuid, all_domains):
    global database, writers, myresolver, resolvers, num_writing_tasks
    myresolver = Utils.make_resolver(resolvers)
    Utils.write_domains(database, uuid, all_domains)
    Utils.write_run(database, uuid, "Spf", zonefilename, len(all_domains), None, samplingrate)
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

