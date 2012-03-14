#!/usr/bin/python

""" DNSdelve module to monitor IPv4 HTTP usage. Is there an IPv4 Web
server?  What's the server signature? Does it have TLS? Etc"""

# Standard modules
import Queue
import random
import getopt
import sys
import os
import time
import socket

# www.dnspython.org
import dns.resolver

# http://pypi.python.org/pypi/python-gnutls/
from gnutls.crypto import *
from gnutls.connection import *
from gnutls.errors import *

# Local
import BaseResult
import BasePlugin
import Utils

__version__ = "0.0"

# Default settings 
database = "dbname=http"
num_writing_tasks = 10
edns_size = 1400
write_delay = 2 # seconds
http_timeout = 15 # seconds
user_agent = "DNSdelve HTTP tester/%s (running with Python %s; http://www.dnsdelve.net; bortzmeyer@nic.fr)" % (__version__, sys.version.split()[0])

# Global
writers = []

class Zone_broken(Exception):
    pass

def module_usage(msg=None):
    print >>sys.stderr, "Usage of this Http module: [-b database_name] [-r resolvers_addresses] [-n N] [-d]"
    if msg is not None:
        print >>sys.stderr, msg

class HttpResult(BaseResult.Result):
    
    def __init__(self):
        self.a_zone = None
        self.a_www_zone = None
        self.http_zone_tests = {}
        self.http_www_zone_tests = {}
        self.https_zone_tests = {}
        self.https_www_zone_tests = {}
        BaseResult.Result.__init__(self)

    def __str__(self):
        if self.a_zone is None:
            num_a_zone = 0
        else:
            num_a_zone = len(self.a_zone)
        if self.a_www_zone is None:
            num_a_www_zone = 0
        else:
            num_a_www_zone = len(self.a_www_zone)
        return "A in ZONE: %i, in www.ZONE: %i" % \
               (num_a_zone, num_a_www_zone)

    def store_host_http_tests(self, name, addresses, uuid, tls=False):
        for address in addresses.keys():
            self.writer.channel.put(["hosts", \
                                     {"uuid": str(uuid), "domain": self.domain, \
                                      "name": name, \
                                      "tls": tls,
                                      "address": address, \
                                      "result": addresses[address][0],
                                      "details": addresses[address][1]}])

    def store(self, uuid):
        if self.a_zone is not None:
            a_zone = [Utils.Inet(a.address) for a in self.a_zone]
            self.store_host_http_tests(self.domain, self.http_zone_tests, uuid)
            self.store_host_http_tests(self.domain, self.https_zone_tests, uuid, tls=True)
        else:
            a_zone = []
        if self.a_www_zone is not None:
            a_www_zone = [Utils.Inet(a.address)  for a in self.a_www_zone]
            self.store_host_http_tests("www.%s" % self.domain, self.http_www_zone_tests, uuid)
            self.store_host_http_tests("www.%s" % self.domain, self.https_www_zone_tests, uuid,
                                       tls=True)
        else:
            a_www_zone = []
        self.writer.channel.put(["tests", {"uuid": str(uuid), "domain":self.domain,
                                 "broken":self.zone_broken,
                                 "a_zone": a_zone, "a_www_zone": a_www_zone}])

def tls_readline(sock):
    buffer = ""
    found = False
    while not found:
        next = sock.recv(1)
        if next == '\r':
            # TODO: can raise GNUTLSError
            next = sock.recv(1)
            if next == '\n':
                found = True
        else:
            buffer = buffer + next
    return buffer
                                                                                    
def test_http(address_str, host_name, tls=None):
    """ Tests an HTTP server and returns a tuple of a boolean
    (True: success) and a string with the detailed message."""
    if tls is None:
        result = socket.getaddrinfo(address_str, "http")
    else:
        result = socket.getaddrinfo(address_str, "https")
    # Keep only the first one
    (family, socktype, proto, garbage, address) = result[0]

    # TODO: if many threads are working, we can fail out of file descriptors
    # Fo a big domain, staying << 1024 threads can be necessary.
    # Augmenting the number of file descriptors does not work on Linux
    # (dnspython uses select, which uses a compile-time value).
    s = socket.socket(family, socktype, proto)
    if tls is None: # Unfortunately, the timeout option does not work with GNU TLS.
        # We only have to hope they will never block...
        s.settimeout(http_timeout)
    if tls is not None:
        s = ClientSession(s, tls)
    try:
        try:
            s.connect(address)
            if tls is not None:
                s.handshake()
        except socket.error, e:
            s.close()
            return (False, "Socket error at connection: %s" % e)
        except GNUTLSError, e:
            return (False, "TLS error: %s" % e)
        if host_name is None or host_name == "":
            request = """HEAD / HTTP/1.0\r\nUser-Agent: %s\r\n\r\n""" % user_agent
        else:
            request = \
                """HEAD / HTTP/1.1\r\nUser-Agent: %s\r\nConnection: close\r\nHost: %s\r\n\r\n""" % \
                (user_agent, host_name)
        s.sendall(request)
        if not tls:
            read_socket = s.makefile('r')
            result = read_socket.readline() # TODO: Is it possible to block for ever, for
            # instance because of a MTU problem?
            # TODO: can raise socket.error (for instance connection reset)
        else:
            result = tls_readline(s)
        if tls is not None:
            s.bye()
        s.close()
    except socket.timeout, e:
        return (False, "Socket timeout (max delay was %i s): %s" % (http_timeout, e))
    # Some HTTP sites return non-ASCII characters in the "reason-phrase" after
    # the status code. It seems legal (RFC 2616, section 6.1.1) Let's replace them
    uresult = unicode(result, "iso-8859-1") # 8859-1 because every byte is legal with it
    # del s
    # TODO: will "del s" help to solve the file descriptors problem?
    # TODO: test the return code? Is 500 or 404 acceptable?
    return (True, "HTTP reply %s" % uresult.encode("US-ASCII", 'replace'))

class Plugin(BasePlugin.Plugin):

    def __init__(self):
        self.myresolver = Utils.make_resolver(resolvers)
        script_path = os.path.realpath(os.path.dirname(sys.argv[0]))
        certs_path = os.path.join(script_path, 'certs')
        cert = X509Certificate(open(certs_path + '/valid.crt').read())
        key = X509PrivateKey(open(certs_path + '/valid.key').read())
        self.credentials = X509Credentials(cert, key)
        BasePlugin.Plugin.__init__(self)

    def one_query(self, qname, qtype):
        zone_broken = False
        try:
            result = self.myresolver.query (qname, qtype)
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            result = None
        except (dns.resolver.NoNameservers, dns.resolver.Timeout):
            # No second chance: the zone is broken, we never try again
            result = None
            zone_broken = True
        return (zone_broken, result)

    def queries(self, zone, nameservers):
        finalresult = HttpResult()
        (zone_broken, result) = self.one_query(zone, 'A');
        if zone_broken:
            raise Zone_broken
        finalresult.a_zone = result
        if result is not None:
            for record in result:
                address = str(Utils.Inet(record.address))
                (success, infos) = test_http(address, zone)
                finalresult.http_zone_tests[address] = [success, infos]
                (success, infos) = test_http(address, zone, tls=self.credentials)
                finalresult.https_zone_tests[address] = [success, infos]
        (zone_broken, result) = self.one_query("www." + zone, 'A');
        if zone_broken:
            raise Zone_broken
        finalresult.a_www_zone = result
        if result is not None:
            for record in result:
                address = str(Utils.Inet(record.address))
                (success, infos) = test_http(address, zone)
                finalresult.http_www_zone_tests[address] = [success, infos]
                (success, infos) = test_http(address, zone, tls=self.credentials)
                finalresult.https_www_zone_tests[address] = [success, infos]
        return finalresult
    
    def query(self, zone, nameservers):
        global writers
        try:
            fullresult = self.queries(zone, nameservers)
        except Zone_broken:
            fullresult = HttpResult()
            fullresult.zone_broken = True
        fullresult.domain = zone
        fullresult.writer = random.choice(writers)
        return fullresult

def config(args):
    global database, num_writing_tasks, resolvers
    try:
        resolvers = None
        optlist, args = getopt.getopt (args, "hn:b:r:d",
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

def start(uuid, all_domains):
    global database, writers, resolvers, num_writing_tasks
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

