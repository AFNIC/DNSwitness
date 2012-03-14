#!/usr/bin/python

""" DNSdelve module to collect Ipv4 and Ipv6 use by checking DNS records.
for typical names. """

# Standard modules
import Queue
import random
import getopt
import sys
import time
import socket

# www.dnspython.org
import dns.resolver
import dns.reversename

# Local
import BaseResult
import BasePlugin
import Utils

__version__ = "0.0"

# Default settings 
database = "dbname=dnsdelve-ip"
num_writing_tasks = 10
edns_size = 1400
write_delay = 2 # seconds
timeout_http_test = 60.0
timeout_smtp_test = 120.0 # RFC 5321 section 4.5.3.2.1 says that the timeout before the initial 220 message is 5 minutes. Here we just wait 2 minutes because it is actually enough (and we have many other tests to run).
# TODO: the timeout of queries?
user_agent = "DNSdelve HTTP tester/%s (running with Python %s; http://www.dnsdelve.net; bortzmeyer@nic.fr)" % (__version__, sys.version.split()[0])
my_smtp_name = "mail.dnsdelve.net" # TODO: something more clever?

# Global
writers = []
zonefilename = None
samplingrate = None

class Zone_broken(Exception):
    pass

def module_usage(msg=None):
    print >>sys.stderr, "Usage of this Ip module: [-b database_name] [-r resolvers_addresses] [-n N] [--no_test] [-4 | -6]"
    if msg is not None:
        print >>sys.stderr, msg

class IpResult(BaseResult.Result):

    def __init__(self):
        self.zone = []
        self.www_zone = []
        self.www_ipv6_zone = []
        self.mx_zone = []
        self.ns_zone = []
        self.http_zone_tests = {}
        self.http_www_zone_tests = {}
        self.http_www_ipv6_zone_tests = {}
        self.mx_tests = {}
        self.ns_tests = {}
        BaseResult.Result.__init__(self)

    def __str__(self):
        num_zone = len(self.zone)
        num_www_zone = len(self.www_zone)
        num_www_ipv6_zone = len(self.www_ipv6_zone)
        num_mx_zone = len(self.mx_zone)
        num_ns_zone = len(self.ns_zone)
        return "AAAA (and A?) in ZONE: %i, in www.ZONE: %i, in www.ipv6.ZONE: %i, MX: %i, NS: %i" % \
               (num_zone, num_www_zone, num_www_ipv6_zone, num_mx_zone, num_ns_zone )

    def store(self, uuid):
        # one test is a string with ip, type, result (bool), details, version_method and version (separated by "|||| ")
        tests_zone = []
        tests_ns_zone = []
        tests_mx_zone = []
        tests_www_zone = []
        tests_www_ipv6_zone = []

        if not no_test:
            for address in self.http_zone_tests.keys():
                tests_zone.append(u"%s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s" % (address, get_cc(address),
                                    get_asn(address),
                                    u'HTTP',
                                    self.http_zone_tests[address][0],
                                    self.http_zone_tests[address][1],
                                    self.http_zone_tests[address][2],
                                    self.http_zone_tests[address][3]))
        else:
            for address in self.zone:
                tests_zone.append(u"%s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s" % (address, '', '', '', '', '', '', ''))

        if not no_test:
            for address in self.ns_tests.keys():
                tests_ns_zone.append(u"%s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s" % (address, get_cc(address),
                                        get_asn(address),
                                        'DNS',
                                        self.ns_tests[address][0],
                                        self.ns_tests[address][1],
                                        self.ns_tests[address][2],
                                        self.ns_tests[address][3]))
        else:
            for address in self.ns_zone:
                tests_ns_zone.append(u"%s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s" % (address, '', '', '', '', '', '', ''))

        if not no_test:
            for address in self.mx_tests.keys():
                tests_mx_zone.append(u"%s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s" % (address, get_cc(address),
                                        get_asn(address),
                                        'SMTP',
                                        self.mx_tests[address][0],
                                        self.mx_tests[address][1],
                                        self.mx_tests[address][2],
                                        self.mx_tests[address][3]))
        else:
            for address in self.mx_zone:
                tests_mx_zone.append(u"%s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s" % (address, '', '', '', '', '', '', ''))

        if not no_test:
            for address in self.http_www_zone_tests.keys():
                tests_www_zone.append(u"%s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s" % (address, get_cc(address),
                                        get_asn(address),
                                        'HTTP',
                                        self.http_www_zone_tests[address][0],
                                        self.http_www_zone_tests[address][1],
                                        self.http_www_zone_tests[address][2],
                                        self.http_www_zone_tests[address][3]))
        else:
            for address in self.www_zone:
                tests_www_zone.append(u"%s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s" % (address, '', '', '', '', '', '', ''))

        if not no_test:
            for address in self.http_www_ipv6_zone_tests.keys():
                tests_www_zone.append(u"%s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s" % (address, get_cc(address),
                                        get_asn(address),
                                        'HTTP',
                                        self.http_www_ipv6_zone_tests[address][0],
                                        self.http_www_ipv6_zone_tests[address][1],
                                        self.http_www_ipv6_zone_tests[address][2],
                                        self.http_www_ipv6_zone_tests[address][3]))
        else:
            for address in self.www_ipv6_zone:
                tests_www_zone.append(u"%s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s|||| %s" % (address, '', '', '', '', '', '', ''))
        self.writer.channel.put(['DBW_CALL_SQL_FUNCTION', 'store', [str(uuid),
                                                                   self.domain,
                                                                   self.zone_broken,
                                                                   tests_zone,
                                                                   tests_ns_zone,
                                                                   tests_mx_zone,
                                                                   tests_www_zone,
                                                                   tests_www_ipv6_zone]])

def get_cc(address):
    """ Retrieve the Country Code of a specific Ip Address.
    We use the python wrapper for libgeoip
    (see http://www.maxmind.com/)
    We store results in a shared dictionary to avoid redoing
    the same lookup in the same run. """
    res = sd_cc.read_or_lock(address)
    if res is None:
        if address.count(':') >= 2: # Ipv6
            res = gi6.country_code_by_addr_v6(address)
        else: # Ipv4
            res = gi.country_code_by_addr(address)
        sd_cc.write_and_unlock(address, res)
        if res is None:
            res = ''
    return res

def get_asn(address):
    """ Retrieve the Autonomous System Number.
    The reverse lookup daemon is provided by Team Cymru
    (see http://www.team-cymru.org/Services/ip-to-asn.html)
    We store results in a shared dictionary to avoid redoing
    the same lookup in the same run. """
    res = sd_asn.read_or_lock(address)
    if res is None:
        r = dns.resolver.Resolver()
        a = dns.reversename.from_address(address).to_text()
        if a.find('in-addr.arpa.') != -1:
            a = a.replace('in-addr.arpa.', 'origin.asn.cymru.com')
        else: # Ipv6
            a = a.replace('ip6.arpa.', 'origin6.asn.cymru.com')
        try:
            q = r.query(a, 'TXT')
            res = q[0].strings[0].split(' | ')[0]
            try:
                int(res)
            except ValueError:
                res = ''
        except Exception:
            res = '' # We never retry
        res = Utils.to_utf8(res)
        sd_asn.write_and_unlock(address, res)
        if res is None:
            res = ''
    return res

def test_http(address_str, host_name):
    """ Tests an HTTP server and returns a tuple of a boolean
    (True: success) and a string with the detailed message."""
    result = socket.getaddrinfo(address_str, "http")
    # Keep only the first one
    (family, socktype, proto, garbage, address) = result[0]
    s = socket.socket(family, socktype, proto)
    s.settimeout(timeout_http_test)
    try:
        s.connect(address)
    except socket.error, e:
        s.close()
        return (False, u"Socket error: %s" % e, '', '')
    if host_name is None or host_name == "":
        request = """GET / HTTP/1.0\r\nUser-Agent: %s\r\n\r\n""" % user_agent
    else:
        request = \
                """GET / HTTP/1.1\r\nUser-Agent: %s\r\nConnection: close\r\nHost: %s\r\n\r\n""" % \
                (user_agent, host_name)
    read_socket = s.makefile('r')
    s.sendall(request)
    try:
        result = read_socket.readline()
    except socket.timeout, e:
        # If there is a MTU problem, maybe HEAD will succeed where GET just failed
        request = request.replace("GET", "HEAD", 1)
        s.sendall(request)
        try:
            result = read_socket.readline()
        except socket.error, e:
            return (False, u"Socket error when reading: %s" % e, '', '')
        return (False, u"GET failed but HEAD succeded: %s" % Utils.to_utf8(result), '', '') # Maybe a MTU problem
    except  socket.error, e:
        s.close()
        return (False, u"Socket error when reading: %s" % e, '', '')

    # Now try to determine the server vendor and version
    version_method = ''
    for i in range (1,20):
        try:
            version = read_socket.readline()
        except socket.error:
            version = ''
            break
        if version is None:
            version = ''
            break
        if version.lower().startswith('server:'):
            version = Utils.to_utf8(version[7:].strip())
            version_method = u'server field'
            break
        version = ''
    s.close()
    return (True, u"HTTP reply %s" % Utils.to_utf8(result.strip()), version_method, version)

def test_smtp(address_str):
    """ Tests a SMTP server and returns a tuple of a boolean
    (True: success) and a string with the detailed message."""
    result = socket.getaddrinfo(address_str, "smtp")
    # Keep only the first one
    (family, socktype, proto, garbage, address) = result[0]
    s = socket.socket(family, socktype, proto)
    s.settimeout(timeout_smtp_test)
    try:
        s.connect(address)
    except socket.error, e:
        s.close()
        return (False, u"Socket error when connecting: %s" % e, '', '')
    read_socket = s.makefile('r')
    try:
        result = read_socket.readline()
    except socket.error, e:
        s.close()
        return (False, u"Socket error when reading the initial message: %s" % e, '', '')
    request = """EHLO %s\r\n""" % my_smtp_name
    s.sendall(request)
    try:
        read_socket.readline()
    except socket.error, e:
        s.close()
        return (False, u"Socket error when reading: %s" % e, '', '')
    s.close()
    # TODO: test the return code? Is 4xx acceptable?
    # TODO: find a method to determine the server vendor and version
    return (True, u"SMTP reply %s" % Utils.to_utf8(result.strip()), '', '')

def test_dns(ns_address, domain):
    """ Tests a name server and returns a tuple of a boolean
    (True: success) a string with the detailed message and a
    string with the server version ('' if unknown)."""
    request = dns.message.make_query(domain, 'SOA')
    timeout = 2
    response = None
    while response is None:
        try:
            response = dns.query.udp(request, ns_address, timeout)
        except dns.exception.Timeout:
            if timeout >= 6:
                return (False, u"Timeout", '', '')
            # Wait a bit and try again
            timeout = timeout * 2
            time.sleep(2)
            response = None
            continue
        except (socket.error, dns.query.UnexpectedSource, dns.exception.FormError):
            return (False, u"Unexpected error", '', '')
        if response.rcode() == dns.rcode.SERVFAIL:
            return (False, u"SERVFAIL", '', '')
        rcode = dns.rcode.to_text(response.rcode())
        # Now try to determine the server vendor and version
        request = dns.message.make_query('version.bind', 'TXT', 'CHAOS')
        version_method = ''
        try:
            response = dns.query.udp(request, ns_address, timeout)
            if response.rcode() == dns.rcode.NOERROR:
                version = Utils.to_utf8(response.answer[0].to_text()[24:-1].strip())
                version_method = 'version.bind'
            else:
                version = ''
        except Exception:
            version = ''
        return (True, rcode, version_method, version)

class Plugin(BasePlugin.Plugin):

    def __init__(self):
        self.myresolver = Utils.make_resolver(resolvers)
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
        finalresult = IpResult()

        if only != 4:
            (zone_broken, result) = self.one_query(zone, 'AAAA');
            if zone_broken:
                raise Zone_broken
            if result is not None:
                finalresult.zone += [a.address for a in result]
        if only != 6:
            (zone_broken, result) = self.one_query(zone, 'A');
            if zone_broken:
                raise Zone_broken
            if result is not None:
                finalresult.zone += [a.address for a in result]
        if not no_test:
            for a in finalresult.zone:
                address = str(Utils.Inet(a))
                # We store all tests of one run in a shared dictionary to avoid testing the same address several time.
                key = 'http_tests' + address
                test = sd_http.read_or_lock(key)
                if test is not None:
                    # This test was already done during this run
                    finalresult.http_zone_tests[address] = test
                else:
                    (success, infos, version_method, version) = test_http(address, zone)
                    finalresult.http_zone_tests[address] = [success, infos, version_method, version]
                    sd_http.write_and_unlock(key, [success, infos, version_method, version])

        if only != 4:
            (zone_broken, result) = self.one_query("www." + zone, 'AAAA');
            if zone_broken:
                raise Zone_broken
            if result is not None:
                finalresult.www_zone += [a.address for a in result]
        if only != 6:
            (zone_broken, result) = self.one_query("www." + zone, 'A');
            if zone_broken:
                raise Zone_broken
            if result is not None:
                finalresult.www_zone += [a.address for a in result]
        if not no_test:
            for a in finalresult.www_zone:
                address = str(Utils.Inet(a))
                key = 'http_tests' + address
                test = sd_http.read_or_lock(key)
                if test is not None:
                    # This test was already done during this run
                    finalresult.http_zone_tests[address] = test
                else:
                    (success, infos, version_method, version) = test_http(address, zone)
                    finalresult.http_www_zone_tests[address] = [success, infos, version_method, version]
                    sd_http.write_and_unlock(key, [success, infos, version_method, version])

        # We do not test "www.ipv6.DOMAIN" on ipv4 (should we?)
        if only != 4:
            (zone_broken, result) = self.one_query("www.ipv6." + zone, 'AAAA');
            if zone_broken:
                raise Zone_broken
            if result is not None:
                finalresult.www_ipv6_zone = [a.address for a in result]
                if not no_test:
                    for record in result:
                        address = str(Utils.Inet(record.address))
                        key = 'http_tests' + address
                        test = sd_http.read_or_lock(key)
                        if test is not None:
                            # This test was already done during this run
                            finalresult.http_www_ipv6_zone_tests[address] = test
                        else:
                            (success, infos, version_method, version) = test_http(address, zone)
                            finalresult.http_www_ipv6_zone_tests[address] = [success, infos, version_method, version]
                            sd_http.write_and_unlock(key, [success, infos, version_method, version])

        (zone_broken, result) = self.one_query(zone, 'MX');
        if zone_broken:
            raise Zone_broken
        if result is not None:
            for mx in result:
                if only != 4:
                    (zone_broken, result) = self.one_query(mx.exchange, 'AAAA');
                    if zone_broken:
                        raise Zone_broken
                    if result is not None:
                        finalresult.mx_zone += [a.address for a in result]
                if only != 6:
                    (zone_broken, result) = self.one_query(mx.exchange, 'A');
                    if zone_broken:
                        raise Zone_broken
                    if result is not None:
                        finalresult.mx_zone += [a.address for a in result]
                if not no_test:
                    for a in finalresult.mx_zone:
                        address = str(Utils.Inet(a))
                        key = 'smtp_tests' + address
                        test = sd_smtp.read_or_lock(key)
                        if test is not None:
                            # This test was already done during this run
                            finalresult.mx_tests[address] = test
                        else:
                            (success, infos, version_method, version) = test_smtp(address)
                            finalresult.mx_tests[address] = [success, infos, version_method, version]
                            sd_smtp.write_and_unlock(key, [success, infos, version_method, version])

        # TODO: this assumes we have the list of nameservers but it is
        # not true if the zone was loaded with --plain-file
        for ns in nameservers:
            if only != 4:
                (zone_broken, result) = self.one_query(ns, 'AAAA');
                if zone_broken:
                    raise Zone_broken
                if result is not None:
                    finalresult.ns_zone += [a.address for a in result]
            if only != 6:
                (zone_broken, result) = self.one_query(ns, 'A');
                if zone_broken:
                    raise Zone_broken
                if result is not None:
                    finalresult.ns_zone += [a.address for a in result]
            if not no_test:
                for a in finalresult.ns_zone:
                    address = str(Utils.Inet(a))
                    key = 'ns_tests' + address
                    test = sd_ns.read_or_lock(key)
                    if test is not None:
                        # This test was already done during this run
                        finalresult.ns_tests[address] = test
                    else:
                        (success, infos, version_method, version) = test_dns(address, zone)
                        finalresult.ns_tests[address] = [success, infos, version_method, version]
                        sd_ns.write_and_unlock(key, [success, infos, version_method, version])

        return finalresult

    def query(self, zone, nameservers):
        global writers
        try:
            fullresult = self.queries(zone, nameservers)
        except Zone_broken:
            fullresult = IpResult()
            fullresult.zone_broken = True
        fullresult.domain = zone
        fullresult.writer = random.choice(writers)
        return fullresult

def config(args, zonefile, sampling):
    global database, num_writing_tasks, resolvers, no_test, only, zonefilename, samplingrate, sd_http, sd_smtp, sd_ns, sd_asn, sd_cc, gi, gi6
    try:
        resolvers = None
        no_test = False
        no_asn = False
        no_cc = False
        only = 0
        optlist, args = getopt.getopt (args, "ht46n:b:r:",
                                       ["help", "num_tasks=", "database=", 
                                        "resolvers=", "no_test", "v4_only", "v6_only"])
        for option, value in optlist:
            if option == "--help" or option == "-h":
                module_usage()
                sys.exit(0)
            elif option == "--num_tasks" or option == "-n":
                num_writing_tasks = int(value)
            elif option == "--resolvers" or option == "-r":
                resolvers = value.split(',')
            elif option == "--no_test" or option == "-t":
                no_test = True
            elif option == "--v4_only" or option == "-4":
                if only == 0:
                    only = 4
                else:
                    only = -1
            elif option == "--v6_only" or option == "-6":
                if only == 0:
                    only = 6
                else:
                    only = -1
            elif option == "--database" or option == "-b":
                database = value
                if database.find('=') == -1:
                    # User only indicated the database name, let's make a proper conninfo
                    database="dbname=%s" % database
            else:
                # Should never occur, it is trapped by getopt
                module_usage("Internal error: unhandled option %s" % option)
                sys.exit(1)
        if only == -1:
            module_usage("Internal error: you can't use -4 and -6 at the same time.")
            sys.exit(1)
        if no_test == False:
            sd_http = Utils.SharedDictionary()
            sd_smtp = Utils.SharedDictionary()
            sd_ns = Utils.SharedDictionary()
            sd_asn = Utils.SharedDictionary()
            try:
                import GeoIP # http://www.maxmind.com/app/python
            except ImportError:
                print "Internal error: you have to install the GeoIP module (or to use the '--no_test' flag)."
                sys.exit(1)
            sd_cc = Utils.SharedDictionary()
            try:
                gi = GeoIP.open("/usr/share/GeoIP/GeoIP.dat",GeoIP.GEOIP_STANDARD)
                gi6 = GeoIP.open("/usr/share/GeoIP/GeoIPv6.dat",GeoIP.GEOIP_STANDARD)
            except Exception:
                print "Internal error: GeoIP databases could not be accessed."
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
    global database, writers, resolvers, num_writing_tasks
    Utils.write_run(database, uuid, "Ip", zonefilename, len(all_domains), None, samplingrate)
    writers = []
    for writer in range(1, num_writing_tasks+1):
        channel = Queue.Queue()
        writers.append(Utils.DatabaseWriter(writer, database, channel, autocommit=True))
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

