#!/usr/bin/python

""" DNSdelve module to check the delegation of all the domains on
all the name servers of the delegating zone. Just to be sure that
Dynamic Update or IXFR did not betray you...

$Id: CheckNameservers.py 8433 2009-04-14 12:29:16Z bortzmeyer $

"""

""" TODO:
* test the SOA to detect old data
"""

import BaseResult
import BasePlugin

import getopt
import sys

import dns.resolver

def module_usage(msg=None):
    print >>sys.stderr, "Usage of this Check-nameservers module: -p parent-zone -e [-n N] "
    if msg is not None:
        print >>sys.stderr, msg

class CheckResult(BaseResult.Result):
    
    def __str__(self):
        return ("%s (%s): %s" % (self.domain, self.nameservers, self.tests))

    def store(self, uuid):
        ok = True
        for ns in self.tests.keys():
            if must_exist and not self.tests[ns]:
                ok = False
                print >>sys.stderr, \
                      ("Houston, we have a problem with %s: name server %s does not have it" % \
                       (self.domain, ns))
            if not must_exist and self.tests[ns]:
                ok = False
                print >>sys.stderr, \
                      ("Houston, we have a problem with %s: name server %s has it" % \
                       (self.domain, ns))
        if ok and debug > 0:
            print "%s is OK" % self
            
class Plugin(BasePlugin.Plugin):

    def __init__ (self):
        if debug > 0:
            print "Plugin starts"
        self.resolver = dns.resolver.Resolver()
        self.resolver.use_edns(1, 0, 1405)
        # TODO: dnspython does not allow to set a "no recursive" flag?
        BasePlugin.Plugin.__init__(self)

    def query(self, zone, nameservers):
        """ MUST NOT raise an exception!!!"""
        # Here, you can perform DNS tests (or tests for other protocols).
        result = CheckResult()
        result.domain = zone
        result.nameservers = nameservers
        result.tests = {}
        if zone == parent_zone[0:-1]:
            return result
        if debug > 1:
            print "Testing %s..." % result.domain
        for auth_ns in parent_nameservers:
            self.resolver.nameservers = [auth_ns,]
            if debug > 1:
                print "\tTesting on %s..." % auth_ns
            try:
                # Do not forget the dot at the end or dnspython follows the search list :-(
                ns_answer = self.resolver.query (zone + ".", 'NS')
                # TODO: check that the delegation is consistent. Difficult since dnspython does
                # not give us the answers
                result.tests[auth_ns] = True
            except dns.resolver.NoAnswer:
                result.tests[auth_ns] = True # Delegation is in the Authority section,
                                             # not the Answer one
            except dns.resolver.NXDOMAIN:
                if serial is not None:
                    # Test it, may be the server has a newer version of the parent zone
                    current_serial = None
                    soa_answer = self.resolver.query (parent_zone, 'SOA')
                    current_serial = soa_answer.rrset.items[0].serial
                    if current_serial > serial:
                        print >>sys.stderr, \
                              ("%s has a newer version %s of the zone %s, " + \
                              "the tests may be meaningless") % \
                              (auth_ns, current_serial, parent_zone)
                        result.tests[auth_ns] = True
                    else:
                        result.tests[auth_ns] = False
                else:
                    result.tests[auth_ns] = False
            except (dns.resolver.NoNameservers, dns.resolver.Timeout):
                # Forget this one, let's move to the next
                pass
        return result

    def final(self):
        if debug > 0:
            print "Plugin ends"

def config(args):
    global parent_nameservers, parent_zone, debug, serial, must_exist
    """ Receive the command-line arguments as an array """
    parent_zone = None
    debug = 0
    serial = None
    must_exist = True
    try:
        optlist, args = getopt.getopt (args, "hn:p:d:e",
                                       ["help", "num_tasks=", "must_NOT_exist",
                                        "parent_zone=", "debug=", "soa="])
        for option, value in optlist:
            if option == "--help" or option == "-h":
                module_usage()
                sys.exit(0)
            elif option == "--num_tasks" or option == "-n":
                num_writing_tasks = int(value)
            elif option == "--debug" or option == "-d":
                debug = int(value)
            elif option == "--soa":
                serial = value
            elif option == "--must_NOT_exist" or option == "-e":
                must_exist = False
            elif option == "--parent_zone" or option == "-p":
                parent_zone = value
                if parent_zone[-1:] != '.':
                    parent_zone = parent_zone + '.'
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
    if parent_zone is None:
        # TODO: deduce it from the zone file?
        module_usage("-p is mandatory")
        sys.exit(1)
    myresolver = dns.resolver.Resolver()
    myresolver.use_edns(1, 0, 1405)
    try:
        result = myresolver.query(parent_zone, "NS")
    except dns.resolver.NXDOMAIN:
        print >>sys.stderr, "Parent zone %s does not exist" % parent_zone
        sys.exit(1)
    except (dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.resolver.Timeout):
        print >>sys.stderr, "Cannot get the name servers of parent zone %s" % parent_zone
        sys.exit(1)
    parent_nameservers = []
    for ns in result.rrset.items:
        result = myresolver.query(ns.target, "A")
        # TODO: AAAA
        for addr in result.rrset.items:
            parent_nameservers.append(addr.address)
    
def start(uuid, domains):
    """ Call it only after config(). You can do what you want with the parameters. """
    print "Check-nameservers module starts, UUID of this run is %s,\n\t%i domains to survey" % \
          (uuid, len(domains))

def final():
    print "Check module ends. Good bye."

if __name__ == '__main__':
    raise Exception("Not yet usable as a main program, sorry")
