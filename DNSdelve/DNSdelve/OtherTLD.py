#!/usr/bin/python

"""
 DNSdelve module to ask other TLD about names that do exist in your TLD.

 Stephane Bortzmeyer <bortzmeyer@nic.fr>

"""

# Standard
import getopt
import sys
import Queue
import time
import random

# www.dnspython.org
import dns.resolver

# Local
import BaseResult
import BasePlugin
import Utils

# Default settings 
database = "essais"
num_writing_tasks = 10
write_delay = 2 # seconds

# Global
writers = []

def module_usage(msg=None):
    print >>sys.stderr, "Usage of this OtherTLD module: -t tld [-b database_name] [-r resolvers_addresses] [-n N] "
    if msg is not None:
        print >>sys.stderr, msg

class OtherTLDsResult(BaseResult.Result):
    
    def __init__(self):
        self.tld = tld
        self.exists = False
        BaseResult.Result.__init__(self)

    def __str__(self):
        return "%s.%s: %s" % (self.label, self.tld, self.exists)

    def store(self, uuid):
        self.writer.channel.put(["tests", {"uuid": str(uuid), "domain":self.domain,
                                           "label":self.label,
                                           "exists":self.exists,
                                           "broken":self.zone_broken,
                                           "tld": self.tld}])
        
class Plugin(BasePlugin.Plugin):

    def config(self):
        global resolvers
        BasePlugin.Plugin.config(self)

    def query(self, zone, nameservers):
        global writers
        zone_broken = False
        fullresult = OtherTLDsResult()
        lastdot = zone.rfind('.') # TODO: it only works for TLDs not for SLDs like co.uk
        label = zone[0:lastdot]
        fullresult.domain = zone
        fullresult.label = label
        self.exists = False
        try:
            result = myresolver.query ("%s.%s" % (label, tld), 'SOA')
            self.exists = True
        except dns.resolver.Timeout:
            zone_broken = True
        except dns.resolver.NoNameservers:
            zone_broken = True
        except dns.resolver.NoAnswer:
            zone_broken = True
        except dns.resolver.NXDOMAIN:
            self.exists = False
        fullresult.zone_broken = zone_broken
        fullresult.tld = tld
        fullresult.exists = self.exists
        fullresult.writer = random.choice(writers)
        return fullresult

def config(args):
    global database, num_writing_tasks, resolvers, tld
    resolvers = None
    tld = None
    try:
        optlist, args = getopt.getopt (args, "hn:b:r:t:",
                                       ["help", "num_tasks=", "database=", 
                                        "resolvers=", "tld="])
        for option, value in optlist:
            if option == "--help" or option == "-h":
                module_usage()
                sys.exit(0)
            elif option == "--num_tasks" or option == "-n":
                num_writing_tasks = int(value)
            elif option == "--resolvers" or option == "-r":
                resolvers = value.split(',')
            elif option == "--tld" or option == "-t":
                tld = value
            elif option == "--database" or option == "-b":
                database = value
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
    if tld is None:
        module_usage("The --tld options is mandatory")
        sys.exit(1)
    if database.find('=') == -1:
        # User only indicated the database name, let's make a proper conninfo
        database="dbname=%s" % database

def start(uuid, all_domains):
    global database, writers, myresolver, resolvers, num_writing_tasks
    myresolver = Utils.make_resolver(resolvers)
    Utils.write_domains(database, uuid, all_domains)
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

