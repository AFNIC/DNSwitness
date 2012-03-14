#!/usr/bin/python

"""
 Tries to detect if a DNS domain uses DNS wildcards (records that
 match every name queried) or not.

 Code and bugs by Stephane Bortzmeyer <bortzmeyer@nic.fr>
 Advices by Joe Abley <jabley@isc.org>

 The algorithm is a bit complicated because the DNS is a complicated
 world and almost every corner case is sure to happen one day or the
 other. So, the obvious algorithm (ask for the star) does not always
 work. That's also why there is an option 'analysis_depth' which
 allows the user to specify the level of "false positives" that is acceptable.
 
 Algorithm, with the maximum 'analysis_depth':

     1) Query a A record for the star (*). (.BZ used to reply to star but
        not to random names)
     
     2) Query a A record for one (or more if there was no reply to the
      star query above) random name (only LDH, 30 to 40
      characters). If there is NXDOMAIN or NOERROR with no answers
      (stupid but .VA does it), yield "no wildcard"
      
     3) Query a A record for another random name and check the reply
     is the same as before. Otherwise, yield"no wildcard"
      
     4) If all A record sets matches (some TLD have a set of records,
     unlike what Verisign did for .COM), yield "wildcard"
      
     5) Otherwise, yield "no wildcard"                        

 $Id: wildcards.py,v 1.2 2003-11-14 12:55:21 bortzmeyer Exp $
"""

import re
import sys
import os
import string
import random
import time
import getopt

# www.dnspython.org
import dns.resolver

# Defaults
qtype = 'A'
number_of_random_tests = 3
analysis_depth = 3
number_of_random_tests = 3
number_of_tests = 2 * number_of_random_tests   
    
class Wildcards:

    # Defaults
    min_domain_length = 40
    max_domain_length = 55
    verbosity = 0
    
    def __init__ (self, addresses = None):
        self.generator = random.Random (time.time())
        self.myresolver = dns.resolver.Resolver()
        if addresses is not None and addresses != []:
            self.myresolver.nameservers = addresses
    
    def random_name (self):
        """ Returns a legal DNS name, choosen randomly. """
        number = self.generator.randrange (self.min_domain_length,
                                           self.max_domain_length)
        name = ""
        for i in range (number):
            name = name + chr (self.generator.randrange (65, 89)) 
            # Only Letters
        return name

    def test_name (self, qname, qtype='A'):
        """ Test if there is a DNS record for this name and this
        type. Returns the values if there are some and None otherwise."""
        values = []
        if self.verbosity:
            print >>sys.stderr, ("Testing a %s record in \"%s\"..." % (qtype, qname))
        try:
            result = self.myresolver.query (qname, qtype)
        except dns.resolver.NXDOMAIN:
            if self.verbosity > 3:
                print >>sys.stderr, "No such domain %s" % qname
            return None
        except dns.resolver.NoAnswer:
            if self.verbosity > 3:
                print >>sys.stderr, "No answer for %s (rr type %s)" % (qname, qtype)
            return None
        except (dns.resolver.NoNameservers, dns.resolver.Timeout):
            if self.verbosity > 3:
                print >>sys.stderr, "Zone %s broken" % qname
            raise
        # TODO: what to do with other qtypes?
        values = [a.address for a in result]
        return values
    
    def has_wildcard (self, domain, type='A'):   
        """ Test if the domain uses DNS wildcards and return the IP
        addresses if so, and None otherwise. """
        addresses_needed = 0
        replies_to_star = False
        addresses_star = self.test_name ("*." + domain, type)
        if addresses_star:
            if self.verbosity:
                print >>sys.stderr, ("%s has probably a %s wildcard (replies to star)" % (domain, type))
            addresses_star.sort()
            replies_to_star = True
        if analysis_depth == 0:
            if addresses_star:
                return addresses_star
            else:
                return None
        addresses_needed = number_of_random_tests # If they do not reply to
                                 # star requests (to evade detection?), we need
                                 # more certainty
        addresses_array = []
        for i in range (addresses_needed):
            random_domain = self.random_name() + "." + domain
            addresses_random = self.test_name (random_domain, type)
            if addresses_random is not None:
                if self.verbosity:
                    print >>sys.stderr, ("%s has probably a %s wildcard" % (domain, type))
                addresses_random.sort()
                addresses_array.append (addresses_random)
            else:
                return None
        if replies_to_star:
            if addresses_array[0] == addresses_star:
                if self.verbosity:
                    print >>sys.stderr, ("%s has regular %s wildcards" % (domain, type))
                return addresses_star
        else:
            wildcard_seen = 0
            addresses_random = addresses_array[0]
            for i in range (addresses_needed-1):
                if addresses_random != addresses_array[i+1]:
                    return None
            if self.verbosity:
                print >>sys.stderr, ("%s has %s wildcards (but does not reply to star)" % (domain, type))
            return addresses_random
        if self.verbosity:
            print >>sys.stderr, ("%s does not really have %s wildcards" % (domain, type))
        return None

def usage():
    print >>sys.stderr, ("Usage: %s [-d] [-t qtype] zone\n" % sys.argv[0])

if __name__ == '__main__':
    checker = Wildcards()
    try:
        optlist, args = getopt.getopt (sys.argv[1:], "v:t:",
                                       ["verbosity=", "type="])
        for option, value in optlist:
            if option == "--verbosity" or option == "-v":
                checker.verbosity = int(value)
            if option == "--type" or option == "-t":
                qtype = string.upper(value)
    except getopt.error, reason:
        print >>sys.stderr, ("%s\n" % reason)
        usage()
        sys.exit(1)
    if len(args) < 1:
        print >>sys.stderr, ("Not enough arguments\n")
        usage()
        sys.exit(1)
    for domain in args:
        addresses = checker.has_wildcard (domain, type=qtype)
        if addresses:
            print "%s has %s wildcards (%s)" % (domain, qtype, str(addresses))
        else:
            print "%s does not have %s wildcards" % (domain, qtype)
