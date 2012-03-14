#!/usr/bin/env python

""" DNSdelve module to study redirections and the underlying resilience of a domain """

# Standard modules
import random
import Queue
import getopt
import sys
import time
import httplib

# www.dnspython.org
import dns.resolver
import dns.reversename

# http://www.crummy.com/software/BeautifulSoup/
from BeautifulSoup import BeautifulSoup, SoupStrainer

# See http://www.icir.org/gregor/tools/registered_domain.html
# and the 'registered_domain' directory
import registered_domain as reg_dom

# Local
import BaseResult
import BasePlugin
import Utils

__version__ = "0.1"

# Default settings 
database = "dbname=dnsdelve-redirections"
num_writing_tasks = 10
write_delay = 2.0 # seconds
http_timeout = 20.0

user_agent = "DNSdelve HTTP tester/%s (running with Python %s; http://www.dnsdelve.net; bortzmeyer@nic.fr)" % (__version__, sys.version.split()[0])

def module_usage(msg=None):
    print >>sys.stderr, "Usage of this module: [-b database_name] [-r resolvers_addresses] [--num_tasks N]"
    if msg is not None:
        print >>sys.stderr, msg

class RedirectionsResult(BaseResult.Result):

    def __init__(self):
        self.domain = None
        self.target = None
        self.crossed_redirections = []
        self.ns_on_path = []

    def __str__(self):
        return "%s lead to %s\nFollowing this (unsorted) path: %s\nDepending on these NS: %s\n" % \
                                    (self.domain, self.target, self.crossed_redirections, self.ns_on_path)

    def store(self, uuid):
        redirections = []
        name_servers = []
        
        for ns in self.ns_on_path:
            pass
        
        for cr in self.crossed_redirections:
            o_auth = strip_url(cr[1])[0]
            t_auth = strip_url(cr[2])[0]
            (o_rd, o_tld, o_asn) = authority_info(o_auth)
            (t_rd, t_tld, t_asn) = authority_info(t_auth)
            redirections.append([cr[0],  # redirection type
                                 cr[1],  # origin
                                 o_auth, # origin: authority
                                 o_rd,   # origin: registered domain
                                 o_tld,  # origin: TLD
                                 o_asn, # origin: AS number
                                 cr[2],  # target
                                 t_auth, # target: authority
                                 t_rd,   # target: registered domain
                                 t_tld,  # target: tld
                                 t_asn, # target: AS number
                                ])

        o_auth = strip_url(self.domain)[0]
        (o_rd, o_tld, o_asn) = authority_info(o_auth)
        if self.target is not None:
            t_auth = strip_url(self.target)[0]
            (t_rd, t_tld, t_asn) = authority_info(t_auth)
        else:
            t_auth = t_rd = t_tld = t_asn = ''

        self.writer.channel.put(['DBW_CALL_SQL_FUNCTION', 'store', [str(uuid),
                                  self.domain,
                                  o_auth,
                                  o_rd,
                                  o_tld,
                                  o_asn,
                                  self.target,
                                  t_auth,
                                  t_rd,
                                  t_tld,
                                  t_asn,
                                  redirections]
                                ])

        for domain in self.ns_on_path.keys():
            for ns in self.ns_on_path[domain]:
                auth = strip_url(ns)[0] # In case someone put an URL in a NS record...
                (rd, tld, asn) = authority_info(auth)
                name_servers.append([ns,
                                     auth,
                                     rd,
                                     tld,
                                     asn])

            if name_servers != []:
                self.writer.channel.put(['DBW_CALL_SQL_FUNCTION', 'store_ns', [str(uuid),
                                          domain,
                                          name_servers]
                                         ])

def authority_info(auth):
    ''' Get the registered domain, the TLD and the AS number of auth. '''
    if auth == '':
        return '', '', ''
    try:
        # Sometime, auth can be an IP...
        dns.inet.af_for_address(auth)
        return '', '', ''
    except Exception:
        # If it's IPv6, it's written between square brackets
        try:
            dns.inet.af_for_address(auth[1:-1])
            return '', '', ''
        except Exception:
            pass
    (garbage, rd, tld) = reg_dom.split_domainname(auth)
    return rd+'.'+tld, tld, get_asn(auth)


def strip_url(url):
    ''' get an URI and return a tuple with Authority and Path '''
    is_https = False
    if url == "Bad redirection":
        return '', '', is_https
    if url.find('http://') == 0:
        url = url[7:]
    elif url.find('https://') == 0:
        url = url[8:]
        is_https = True
    res = [url,]
    for sep in ('/', '?', '&', '#'): # some separators
        tres = url.split(sep, 1)
        if len(tres) != 1 and len(tres[0]) < len(res[0]):
            res = [tres[0], sep + tres[1]]
    if res[0][-1:] == '.':
        res[0] = res[0][:-1] # remove the trailing dot
    port = res[0].split(':') # a port number may be in the URL
    if len(port) == 2:
        try:
            int(port[1])
            res[0] = port[0]
            res[1] = port[1] + res[1]
        except ValueError:
            pass
    if len(res) == 1:
        return res[0], '', is_https
    else:
        res.append(is_https)
        return res

def get_ip(r, zone):
    """ Returns a list of all IP for a zone.
    query should be 'A' or 'AAAA'. """
    res = []
    try:
        q = r.query(zone, 'A')
        res = [a.address for a in q]
    except Exception:
        pass
    try:
        q = r.query(zone, 'AAAA')
        res.extend([a.address for a in q])
    except Exception:
        pass
    return res

def get_asn(zone):
    """ Returns ASN for a domain in form of a string.
    The separator is a '|'. """
    asn = []
    r = Utils.make_resolver(resolvers)
    ip = get_ip(r, zone)
    for address in ip:
        res = sd_asn.read_or_lock(address)
        if res is None:
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
                    res = None
            except Exception:
                res = None # We never retry
            res = Utils.to_utf8(res)
            sd_asn.write_and_unlock(address, res)
        if res is not None and res != 'None':
            asn.append(res)
    asn = list(set(asn))
    if len(asn) > 0:
        res = asn[0]
        if len(asn) > 1:
            for a in asn[1:]:
                res = res+u'|%s' % a
    else:
        res = ''
    return res

class Plugin(BasePlugin.Plugin):

    def __init__ (self):
        self.myresolver = Utils.make_resolver(resolvers)
        BasePlugin.Plugin.__init__(self)

    def detect_cname_redirected(self, zone):
        """ detect and follow recursively CNAME records in the DNS. 
        Returns a list of tuple like [('CNAME', 'origin', 'target')] """
        cname_path = []
        orig = zone
        r = self.myresolver
        while True:
            try:
                res = r.query(orig, 'CNAME')
                target = (u'CNAME', orig, Utils.to_utf8(res[0].to_text()))
                if target in cname_path:
                    break # TODO handle this in a better way? (infinite loop)
                cname_path.append(target)
                orig = target[2]
            except Exception:
                break # No redirection (end of path) or a problem occurred
        return cname_path

    def detect_http_redirected(self, orig):
        """ Detect if orig is HTTP or HTML (refresh) redirected.
        Returns a tuple like ('redirection-type', 'origin', 'target') """
        try:
            s_auth, s_path, is_https = strip_url(orig)
            if is_https:
                print '\n\nPLOP  %s%s\n\n' % (s_auth, s_path)
                conn = httplib.HTTPSConnection(s_auth, timeout=http_timeout)
            else:
                conn = httplib.HTTPConnection(s_auth, timeout=http_timeout)
            conn.request('GET', s_path, headers={'User-Agent': user_agent})
            r = conn.getresponse()
        except Exception, e:
            return (None, None, None)
        # Detect HTTP redirection
        if r.status in (301, 302, 303):
            for field in r.getheaders():
                if field[0].lower() == 'location':
                    # try do deal with relative URL (some naughty persons ignore RFC 2616 section-14.30)
                    if field[1][0] == '/':
                        field = (field[0], orig + field[1])
                    # Try to guess when it does not begin by a '/'
                    elif field[1].find('http://') != 0 and field[1].find('https://') != 0:
                        field = (field[0], orig + '/' + field[1])
                    return (str(r.status), orig, field[1])
        else:
            # Try to detect HTML redirection
            try:
                strainer = SoupStrainer('meta')
                soup = BeautifulSoup(''.join(r.read()), parseOnlyThese=strainer)
                for tag in soup:
                    for attr in tag.attrs:
                        if attr[0] == 'http-equiv' and attr[1].lower() == 'refresh':
                            for attr in tag.extract().attrs:
                                if attr[0] == 'content':
                                    i = attr[1].lower().find('url=')
                                    if i != -1:
                                        target = attr[1][i+4:]
                                        # Try to deal with relative URL (same as above)
                                        if target[0] == '/':
                                            target = orig + target
                                        # Try to guess when it does not begin by a '/'
                                        elif target.find('http://') != 0 and target.find('https://') != 0:
                                            target = orig + '/' + target
                                        return ('refresh', orig, target)
            except Exception:
                pass
        return (None, orig, None) # No redirection

    def get_name_servers(self, uri):
        """ Returns a list of name servers for uri (authority).
        If it does not found any NS for uri, it retries with the upper level.
        It uses a shared dictionary internally (across all threads) to avoid
        redoing the same query multiple times. """
        res = None
        r = self.myresolver
        try:
            res = r.query(uri, 'NS')
        except dns.resolver.NoAnswer:
            # This may be CNAME redirected
            red = self.detect_cname_redirected(uri)
            if red != []:
                res = self.get_name_servers(red[-1][2])
        except Exception:
            res = [] # give up (NXDOMAIN or Timeout or NoNameservers)
        if res is None:
            # try to go up
            if uri != reg_dom.split_domainname(uri)[2]: 
                new_uri = uri[uri.find('.')+1:]
                res = self.get_name_servers(new_uri)
            else:
                # We just tested a TLD and we did not found any NS?
                # We may have a problem here :-(
                res = []
        if type(res) == dns.resolver.Answer:
            res = [a.to_text() for a in res]
        return res

    def redirected(self, uri):
        ''' Test uri and return a tuple with:
        - the true visible target (as if you typed uri in a browser)
        - An array of crossed redirections. Each one is like (redirection_type, origin, target)
        - A dictionary of crossed NS like {'authority': [ns1, ns2, ...], ...} '''
        redirection_path = []
        ns_on_path = {}
        orig = uri
        recursion = 0
        while True:
            target = self.detect_http_redirected(uri)
            redirection_path.extend(self.detect_cname_redirected(strip_url(uri)[0]))
            if target[1] == target[2]:
                break
            uri = target[2]
            if uri is None:
                break
            redirection_path.append(target)
            recursion += 1
            if recursion > 15:
                # Infinite loop (redirected at least 10 times)
                return u"Bad redirection", [], {}
        redirection_path = list(set(redirection_path)) # remove duplicates
        base = strip_url(orig)[0]
        ns_on_path[base] = self.get_name_servers(base)
        for red in redirection_path:
            base = strip_url(red[2])[0]
            if not ns_on_path.has_key(base):
                ns_on_path[base] = self.get_name_servers(base)
        return target[1], redirection_path, ns_on_path

    def query(self, zone, nameservers):
        global writers
        result = RedirectionsResult()
        # TODO test www.zone? Only if zone leads nowhere? Or each time?
        result.domain = zone
        (result.target, result.crossed_redirections, result.ns_on_path) = self.redirected(zone)
        result.writer = random.choice(writers)
        return result


def config(args, zonefile, sampling):
    global database, num_writing_tasks, resolvers, zonefilename, samplingrate, sd_asn
    try:
        resolvers = None
        optlist, args = getopt.getopt (args, "hn:b:r:",
                                       ["help", "num_tasks=", "database=", "resolvers="])
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
    zonefilename = zonefile
    samplingrate = sampling
    sd_asn = Utils.SharedDictionary()

def start(uuid, all_domains):
    global database, writers, resolvers, num_writing_tasks
    Utils.write_run(database, uuid, "Redirections", zonefilename, len(all_domains), None, samplingrate)
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
    raise Exception("This is a module for DNSdelve, you can't run it as a main program.")

