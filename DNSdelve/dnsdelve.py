#!/usr/bin/python

""" Main driver program for DNSdelve """

# Standard
import threading
import Queue
import time
import sys
import getopt
import random
import uuid
import traceback

# Local
import DNSdelve.ParseZonefile as ParseZonefile
import DNSdelve.GetFromFile as GetFromFile
import DNSdelve.Utils as Utils
from DNSdelve.Utils import fatal, error

def usage(msg=None):
    print >>sys.stderr, "Usage: %s [options] -m module zonefile [module options]" % sys.argv[0]
    if msg is not None:
        print >>sys.stderr, msg
   
class Querier(threading.Thread):

    def __init__(self, id, uuid, channel, report_channel):
        threading.Thread.__init__(self, name="DNS Querier %i" % id)
        self.channel = channel
        self.uuid = uuid
        self.report = report_channel
        if debug > 1:
            print "%s starts" % self.getName()
        
    def run(self):
        myplugin = Plugin()
        myplugin.config()
        handled = 0
        domain = None
        while True:
            (domain, nameservers) = self.channel.get()
            if domain == "" or domain is None:
                break
            handled = handled + 1
            try:
                result = myplugin.query(domain, nameservers)
            except Exception:
                print >>sys.stderr, traceback.format_exc()
                fatal ("%s: Cannot query domain %s\n\n" % (self.getName(), domain))
            if debug > 2:
                print "Result for %s: \"%s\"" % (domain, result)
            try:
                result.store(self.uuid)
                del result
            except Exception:
                print >>sys.stderr, traceback.format_exc()
                fatal ("%s: Cannot store domain %s\n\n" % \
                       (self.getName(), domain))
            if handled % report_every_n_domains == 0:
                self.report.put("PROGRESS:%s:%i" % (self.getName(), handled))
                handled = 0 # "handled" is not the total from the beginning of the thread,
                # it is the number of domains processed since the last report.
        self.report.put("FINAL:%s:%i" % (self.getName(), handled))
        myplugin.final()
        if debug > 1:
            print "%s ends" % self.getName()
         
class Report(threading.Thread):
    """ Be sure to create only one! """
    def __init__(self, channel):
        threading.Thread.__init__(self, name="report")
        self.channel = channel

    def run(self):
        domains_handled = 0
        old_threshold = 0
        while True:
            info = self.channel.get()
            if info == "" or info is None:
                break
            fields = info.split(":")
            if fields[0] == "PROGRESS" or fields[0] == "FINAL":
                domains_handled = domains_handled + int(fields[2])
            elif fields[0] == "FEED":
                pass # TODO: print something
            else:
                if debug > 0:
                    print "Warning: unknown message type %s" % fields[0]
            if debug > 1:
                print "%s (%s s elapsed) Received stats info from %s: \"%s\"" % \
                      (time.strftime("%H:%M:%S", time.localtime(time.time())),
                       int(time.time()-start),
                       fields[1], info)
            if debug > 0:
                # TODO: replace 10 by a sensibly-computed value
                if domains_handled % (report_every_n_domains * 10) == 0 and \
                   domains_handled > old_threshold:
                    print("%s (%s s elapsed) %i/%i (%i %%) domains handled, %i per second" % \
                          (time.strftime("%H:%M:%S", time.localtime(time.time())),
                           int(time.time()-start),
                           domains_handled, num_domains,
                           int((domains_handled*100)/num_domains),
                           int(domains_handled / (time.time()-start))))
                    old_threshold = domains_handled
        if debug > 0:
            print("%s (%s s elapsed) Report task ending" % \
                  (time.strftime("%H:%M:%S", time.localtime(time.time())),
                           int(time.time()-start)))
            print("%i/%i (%i %%) domains handled, %i per second" % \
                  (domains_handled, num_domains,
                   int((domains_handled*100)/num_domains),
                   int(domains_handled / (time.time()-start))))
            
if __name__ != '__main__':
    raise Exception("Only usable as a main program")

module = None
debug = 0
num_threads = 10
percentage_domains = 1
report_every_n_domains = 5000
plain_input_file = False
try:
    optlist, args = getopt.getopt (sys.argv[1:], "hd:n:m:p:r:l",
                               ["help", "debug=", "num_threads=", "percentage=", "plain_file",
                                "report_every=", "module="])
    for option, value in optlist:
        if option == "--help" or option == "-h":
            usage()
            sys.exit(0)
        elif option == "--num_threads" or option == "-n":
            num_threads = int(value)
        elif option == "--report_every" or option == "-r":
            report_every_n_domains = int(value)
        elif option == "--percentage" or option == "-p":
            percentage_domains = float(value)
            if percentage_domains <= 0 or percentage_domains > 1:
                usage("The percentage of domains to test must be > 0 and <= 1")
                sys.exit(1)
        elif option == "--plain_file" or option == "-l":
            plain_input_file = True
        elif option == "--debug" or option == "-d":
            debug = int(value)
        elif option == "--module" or option == "-m":
            module = value
        else:
            print >>sys.stderr, "Unknown option %s" % option
            usage()
            sys.exit(1)
except getopt.error, reason:
    usage(reason)
    sys.exit(1)
if len(args) < 1:
    usage()
    sys.exit(1)
zonefile = args[0]
if module is None:
    usage("-m option is mandatory")
    sys.exit(1)
module_args = args[1:]

try:
    exec ("import DNSdelve.%s as %s" % (module, module))
except ImportError, message:
    fatal ("No such module " + module + \
           " in my Python path: " + str(message))
except Exception:
    fatal ("Module " + module + " cannot be loaded: " + \
           str(sys.exc_type) + ": " + str(sys.exc_value) + \
           ".\n    May be a missing or erroneous option?")
try:
    exec ("from DNSdelve.%s import Plugin" % module)
except ImportError, message:
    fatal ("No constructor Plugin in " + module + \
           ": " + str(message))
try:
    exec ("%s.config(%s, \"%s\", %s)" % (module, str(module_args), zonefile, percentage_domains))
except AttributeError, message:
    fatal ("No method (or invalid methode) config() in " + module + \
           ": " + str(message))
if debug > 0:
    # TODO: test the size of the zone file before alarming the user...
    print "Parsing zone file %s, this may be very long..." % zonefile
parsing = time.time()
if not plain_input_file:
    total_domains = ParseZonefile.parse(zonefile)
else:
    total_domains = GetFromFile.parse(zonefile)
parsing = time.time()-parsing
if debug > 0:
    print "Parsing took %i seconds" % parsing
if len(total_domains) == 0:
        fatal("Zero domain found in %s. Wrong format?" % zonefile)
if percentage_domains == 1:
    num_domains = len(total_domains)
    domains = total_domains
else:
    num_domains = int(len(total_domains) * percentage_domains)
    if num_domains == 0:
        fatal("Percentage too low: %f (for a total of %i domains)" % \
              (percentage_domains, len(total_domains)))
    domains = random.sample(total_domains, num_domains)
domains_per_thread = int(num_domains/num_threads) + 1
myuuid = uuid.uuid4() # RFC 4122
if debug > 0:
    print "Analyzing %i domains (around %i for each of the %i threads), UUID %s" % \
          (num_domains, domains_per_thread, num_threads, myuuid)
try:
    exec ("%s.start(\"%s\", %s)" % (module, myuuid, str(domains)))
except AttributeError, message:
    fatal ("No method start() in " + module + \
           ": " + str(message))
queriers = {}
channels = {}
report_channel = Queue.Queue(0)
report = Report(report_channel)
report.start()
for querier_num in range(1, num_threads+1):
    channels[querier_num] = Queue.Queue(0)
    queriers[querier_num] = Querier(querier_num, myuuid,
                                    channels[querier_num], report_channel)
    queriers[querier_num].start()
if debug > 0:
    print "%i threads running (including main)" % \
          threading.activeCount()
    print ""
start = time.time()
domain_no = 0
for domain in domains:
    domain_no = domain_no + 1
    querier_num = (domain_no % num_threads) + 1
    channels[querier_num].put([domain, total_domains[domain]])

for querier_num in range(1, num_threads+1):
    channels[querier_num].put([None, None])
for querier_num in range(1, num_threads+1):
    queriers[querier_num].join()

try:
    exec ("%s.final()" % (module))
except AttributeError, message:
    fatal ("No method final() in " + module + \
           ": " + str(message))

report_channel.put(None)
report.join()
if debug > 0:
    print "End of run %s" % myuuid
    
