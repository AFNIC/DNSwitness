#!/usr/bin/python

""" DNSdelve module to detect DNS wildcards use. Prone to false negatives. """

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
import DNSwildcards

# Default settings 
database = "wildcards"
num_writing_tasks = 10
write_delay = 2 # seconds
# TODO: the timeout of queries?

# Global
writers = []

def module_usage(msg=None):
    print >>sys.stderr, "Usage of this Wildcards module: [-b database_name] [-r resolvers_addresses] [-n N] "
    if msg is not None:
        print >>sys.stderr, msg

class WildcardsResult(BaseResult.Result):
    
    def __init__(self):
        self.wildcards = None
        BaseResult.Result.__init__(self)

    def __str__(self):
        return "Wildcards: %s" % (self.wildcards)

    def store(self, uuid):
        self.writer.channel.put(["tests", {"uuid": str(uuid), "domain":self.domain,
                                 "broken":self.zone_broken,
                                 "wildcards": self.wildcards}])
        
class Plugin(BasePlugin.Plugin):

    def config(self):
        global resolvers
        self.checker = DNSwildcards.Wildcards(resolvers)
        self.checker.verbosity = 0 # TODO: allow to change it
        BasePlugin.Plugin.config(self)

    def query(self, zone, nameservers):
        global writers
        zone_broken = False
        wildcards = None
        try:
            wildcards = self.checker.has_wildcard (zone)
        except dns.resolver.Timeout:
            zone_broken = True
        except dns.resolver.NoNameservers:
            zone_broken = True
        fullresult = WildcardsResult()
        fullresult.zone_broken = zone_broken
        if wildcards is None:
            fullresult.wildcards = None
        else:
            fullresult.wildcards = [Utils.Inet(a) for a in wildcards]
        fullresult.domain = zone
        fullresult.writer = random.choice(writers)
        return fullresult

def config(args):
    global database, num_writing_tasks, resolvers
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

