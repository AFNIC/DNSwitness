#!/usr/bin/python

zonefile = "fr.db" # Today 1197789 in ".FR"
resolvconf = "/does/not/exist/use/localhost" # This will force DNS Python to use 127.0.0.1 as a resolver
num_threads = 10000
# Tests:
#
# 1000 threads on .FR: 
# 15:23:30 (2477 s elapsed) Received stats info from Querier 113
# Stats task ending
# 1197789/1197789 (100 %) domains handled, 483 per second (754 positive, 0 %)
#
# 10000 threads on .FR:
# 16:01:36 (2169 s elapsed) Received stats info from Querier 7241
# Stats task ending
# 1197789/1197789 (100 %) domains handled, 552 per second (757 positive, 0 %)
#
# 100 threads on .FR:
# [Interrupted because too slow]
# 16:45:39 (2513 s elapsed) Received stats info from Querier 34
# 235000/1197789 (19 %) domains handled, 93 per second (150 positive, 0 %)

report_every_n_domains = 500
debug = 1

import threading
import Queue
import time

# www.dnspython.org
import dns.resolver

# Local
import ParseZonefile

class Querier(threading.Thread):

    def __init__(self, id, channel, stats_channel):
        threading.Thread.__init__(self, name=str(id))
        self.channel = channel
        self.stats = stats_channel
        if debug > 0:
            print "Querier %s starts" % self.getName()

    def run(self):
        name = self.getName()
        myresolver = dns.resolver.Resolver(filename=resolvconf)
        myresolver.use_edns(1, 0, 1400)
        if debug > 2:
            print "Querier %s works through %s" % (name, myresolver.nameservers)
        handled = 0
        positive = 0
        while True:
            domain = self.channel.get()
            if domain == "" or domain is None:
                break
            handled = handled + 1
            if debug > 2:
                print "Querier %s works on %s" % (name, domain)
            try:
                aaaa = myresolver.query ("www.%s" % domain, 'AAAA')[0]
                positive = positive + 1
            except dns.resolver.NoAnswer: 
                aaaa = None
            except dns.resolver.NoNameservers: 
                aaaa = None
            except dns.resolver.NXDOMAIN:
                aaaa = None
            except dns.resolver.Timeout:
                aaaa = None
            if debug > 2:
                print "Querier %s got result %s for %s" % (name, aaaa, domain)
            if handled % report_every_n_domains == 0:
                self.stats.put("PROGRESS:Querier %s:%i:%i" % (name, handled, positive))
                handled = 0
                positive = 0
        self.stats.put("FINAL:Querier %s:%i:%i" % (name, handled, positive))
        if debug > 0:
            print "Querier %s ends" % self.getName()
                  
class Stats(threading.Thread):
    """ Be sure to create only one! """
    def __init__(self, channel):
        threading.Thread.__init__(self, name="stats")
        self.channel = channel

    def run(self):
        domains_handled = 0
        positive_domains = 0
        old_threshold = 0
        while True:
            info = self.channel.get(block=True)
            if info == "" or info is None:
                break
            fields = info.split(":")
            if fields[0] == "PROGRESS" or fields[0] == "FINAL":
                domains_handled = domains_handled + int(fields[2])
                positive_domains = positive_domains + int(fields[3])
            elif fields[0] == "FEED":
                pass # TODO: print something
            else:
                if debug > 0:
                    print "Warning: unknown message type %s" % fields[0]
            if debug > 0:
                print "%s (%s s elapsed) Received stats info from %s" % \
                      (time.strftime("%H:%M:%S", time.localtime(time.time())),
                       int(time.time()-start),
                       fields[1])
                if domains_handled % (report_every_n_domains * 10) == 0 and \
                   domains_handled > old_threshold:
                    print("%i/%i (%i %%) domains handled, %i per second (%i positive, %i %%)" % \
                          (domains_handled, num_domains,
                           int((domains_handled*100)/num_domains),
                           int(domains_handled / (time.time()-start)),
                           positive_domains, int((positive_domains*100)/domains_handled)))
                    old_threshold = domains_handled
        if debug > 0:
            print "Stats task ending"
            print("%i/%i (%i %%) domains handled, %i per second (%i positive, %i %%)" % \
                  (domains_handled, num_domains,
                   int((domains_handled*100)/num_domains),
                   int(domains_handled / (time.time()-start)),
                   positive_domains, int((positive_domains*100)/domains_handled)))
            
if __name__ == '__main__':
    domains = ParseZonefile.parse(zonefile)
    num_domains = len(domains)
    if debug > 0:
        print "%i domains in %s" % (num_domains, zonefile)
    domains_per_thread = int(num_domains/num_threads) + 1
    if debug > 0:
        print "\t%i domains for each of the %i threads" % (domains_per_thread, num_threads)    
    queriers = {}
    channels = {}
    stats_channel = Queue.Queue(0)
    stats = Stats(stats_channel)
    stats.start()
    for querier_num in range(1, num_threads+1):
        channels[querier_num] = Queue.Queue(0)
        queriers[querier_num] = Querier(querier_num, channels[querier_num], stats_channel)
        queriers[querier_num].start()
    if debug > 0:
        print "%i threads running (including main)" % \
              threading.activeCount()
        print ""
    start = time.time()
    domain_no = 0
    for domain in domains:
        # TODO: randomize the list of domains, first
        # TODO: allow a subset of domains
        domain_no = domain_no + 1
        querier_num = (domain_no % num_threads) + 1
        channels[querier_num].put(domain)
        if domain_no % (report_every_n_domains * 10) == 0:
                stats_channel.put("FEED:Main:%s" % domain_no)
    for querier_num in range(1, num_threads+1):
        channels[querier_num].put(None)
    for querier_num in range(1, num_threads+1):
        queriers[querier_num].join()
    stats_channel.put(None)
