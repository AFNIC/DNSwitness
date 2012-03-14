#!/usr/bin/python

""" DNSdelve *dummy* module to illustrate what needs to be put in a
module. This module mostly prints things, that's all.

$Id: Dummy.py 10130 2010-09-06 08:46:27Z bortzmeyer $

"""

import BaseResult
import BasePlugin

class DummyResult(BaseResult.Result):
    
    def __str__(self):
        return "Dummy result"

    def store(self, uuid):
        print "Dummy storage of data for %s" % self.domain

class Plugin(BasePlugin.Plugin):

    def __init__ (self):
        print "Plugin starts"
        BasePlugin.Plugin.__init__(self)

    def query(self, zone, nameservers):
        """ MUST NOT raise an exception!!!"""
        # Here, you can perform DNS tests (or tests for other protocols).
        result = DummyResult()
        result.domain = zone
        return result

    def final(self):
        print "Plugin ends"

def config(args, zonefile, sampling):
    """ Receive the command-line arguments as an array """
    print "Dummy module received arguments \"%s %s %s\" and will dutifully ignore them" % (args, zonefile, sampling)

def start(uuid, domains):
    """ Call it only after config(). You can do what you want with the parameters. """
    print "Dummy module starts, UUID of this run is %s,\n\t%i domains to survey" % \
          (uuid, len(domains))
    # That is typically where you would create the DNS resolver with things like:
    # myresolver = dns.resolver.Resolver()
    # myresolver.use_edns(1, 0, 2048)

def final():
    print "Dummy module ends. Good bye."

if __name__ == '__main__':
    raise Exception("Not yet usable as a main program, sorry")
