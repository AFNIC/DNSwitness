#!/usr/bin/python

""" DNSdelve Zonecheck, to test the correctness of DNS zones. See
<http://www.zonecheck.fr/>

$Id: Zonecheck.py 11696 2011-12-19 14:00:37Z bortzmeyer $

"""

import BaseResult
import BasePlugin
import Utils

import getopt
import Queue
import time
import random
import subprocess
import sys

# Default settings 
database = "dbname=zonecheck"
num_writing_tasks = 10
write_delay = 2 # seconds
timelimit = 300

def module_usage(msg=None):
    print >>sys.stderr, "Usage of this Zonecheck module: [-b database_name] [-n N] [-p zc_prfile_file] [-v zc_verbosity] [-e zc_error] [-t N]"
    if msg is not None:
        print >>sys.stderr, msg

class ZonecheckResult(BaseResult.Result):
    
    def __init__(self):
        self.ok = False
        self.message = None
        BaseResult.Result.__init__(self)
        
    def __str__(self):
        if self.ok:
            info = "OK"
        else:
            info = "ERROR\n%s" % self.message
        return info

    def store(self, uuid):
        global profile
        self.writer.channel.put(["tests", {"uuid": str(uuid), "domain":self.domain,
                                           "profile": profile,
                                           "status": self.ok, "message": self.message}])

class Plugin(BasePlugin.Plugin):

    def __init__ (self):
        print "Plugin starts"
        BasePlugin.Plugin.__init__(self)

    def query(self, zone, nameservers):
        """ MUST NOT raise an exception!!!"""
        global writers, profile, verbose, erroropt, timelimit
        result = ZonecheckResult()
        result.domain = zone
        verbose_option = '--verbose=' + verbose
        error_option   = '--error=' + erroropt
        # TODO: the name servers
        result.writer = random.choice(writers)
        over = False
        attempts = 0
        while not over:
            if timelimit is not None:
                try:
                    zonecheck = subprocess.Popen(["timelimit", "-t", str(timelimit), "-T", str(timelimit/10 + 1),
                                              "zonecheck", "--profile", profile, verbose_option, error_option, zone],
                           shell=False,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
                except OSError:
                    result.ok = False
                    result.message = "OS error, probably because the timelimit program is not available"
                    return result
            else:
                try:
                    zonecheck = subprocess.Popen(["zonecheck", "--profile", profile, verbose_option, error_option, zone],
                           shell=False,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
                except OSError:
                    result.ok = False
                    result.message = "OS error, probably because the zonecheck program is not available"
                    return result
            output = zonecheck.stdout.readlines()
            error = zonecheck.stderr.readlines()
            zonecheck.wait()
            attempts += 1
            if not zonecheck.returncode:
                result.ok = True
                over = True
                # TODO: add the output, we may have warnings
                result.message = None
            else:
                result.ok = False
                result.message = "".join(output) + "\n" + "".join(error)
                if attempts >= 4:
                    over = True
                elif result.message.lower().find("timeout") >= 0:
                    # Zonecheck may have transient timeouts
                    print ("DEBUG: retrying %s..." % zone);
                    time.sleep(random.randint(10, 20))
                    # And start again
                    over = False
                # TODO: the case of Ruby thread failures, as well? Such as
                # "undefined method `empty?' for nil:NilClass"
                else:
                    over = True
        return result

    def final(self):
        print "Plugin ends"

def config(args, zonefile, sampling):
    """ Receive the command-line arguments as an array """
    global database, num_writing_tasks, zonefilename, samplingrate, profile, verbose, erroropt, timelimit
    resolvers = None
    profile = None
    verbose = '-i,x,d,f'
    erroropt = 'ds,ns'
    try:
        optlist, args = getopt.getopt (args, "hn:b:p:v:t:",
                                       ["help", "num_tasks=", "database=", 
                                        "profile=", "verbose=", "error=", "timelimit="])
        for option, value in optlist:
            if option == "--help" or option == "-h":
                module_usage()
                sys.exit(0)
            elif option == "--num_tasks" or option == "-n":
                num_writing_tasks = int(value)
            elif option == "--timelimit" or option == "-t":
                timelimit = int(value)
                if timelimit == 0:
                    timelimit = None
            elif option == "--profile" or option == "-p":
                profile = value
            elif option == "--verbose" or option == "-v":
                verbose = value
            elif option == "--error" or option == "-e":
                erroropt = value
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
    if profile is None:
        profile = "default"
        
def start(uuid, domains):
    global writers
    """ Call it only after config(). You can do what you want with the parameters. """
    print "Zonecheck module starts, UUID of this run is %s,\n\t%i domains to survey" % \
          (uuid, len(domains))
    Utils.write_domains(database, uuid, domains)
    Utils.write_run(database, uuid, "Zonecheck", zonefilename, len(domains),
                    None, samplingrate)
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
    print "Zonecheck module ends. Good bye."

if __name__ == '__main__':
    raise Exception("Not yet usable as a main program, sorry")
