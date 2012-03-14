#!/usr/bin/python

""" Various non-mandatory utilities for DNSdelve. They can be useful
for module authors """

import threading
import sys

# www.dnspython.org
import dns.resolver

# http://www.initd.org/Software/psycopg/
import psycopg2
from psycopg2.extensions import adapt, register_adapter, AsIs

edns_size = 1400

def fatal(msg):
    """ Prints msg and stops the whole system. TODO: test if it stops all the threads. """
    print  >>sys.stderr, "Fatal: %s" % msg
    sys.exit (1)

def error(msg):
    """ Prints msg"""
    print  >>sys.stderr, "Error: %s" % msg

def write_run(conninfo, uuid, module, zonefilename, numdomains, totaldomains, percentage):
    """ Put the run's meta-data in the database identified by
    conninfo"""
    connection = psycopg2.connect(conninfo)
    cursor = connection.cursor()
    cursor.execute("""INSERT INTO Runs (uuid, module, zonefile, totaldomains, numberdomains, samplingrate)
                             VALUES (%s, %s, %s, %s, %s, %s);""",
                       (uuid, module, zonefilename, totaldomains, numdomains, percentage))
    # TODO: bad idea. This makes "phantom" runs with no data. We
    # should have one commit for everything
    cursor.execute("COMMIT;")
    cursor.close()
    connection.close()
    
def write_domains(conninfo, uuid, domains):
    """ Put the domains in the database identified by conninfo, for easier searches """
    connection = psycopg2.connect(conninfo)
    cursor = connection.cursor()
    # TODO: try to make it faster with something like COPY?
    for domain in domains:
        cursor.execute("""INSERT INTO Zones (uuid, name) VALUES (%s, %s);""",
                       (uuid, domain))
    cursor.execute("COMMIT;")
    cursor.close()
    connection.close()

class Inet(object):
    """ Handles IP addresses as Python objects """
    def __init__(self, addr):
        """ addr is a text string representing the address. Never call this constructor with
        unchecked data, there is no protection against injection """
        # TODO: check it is an IP address
        self.addr = addr

    def __str__(self):
        return self.addr
    
def adapt_inet(address):
    return AsIs("'%s'::inet" % address.addr)

class DatabaseWriter(threading.Thread):
   """ A class of threads which write in the DBMS. At initialization
   time, you need to provide it with a communication channel, a Python
   Queue. You can then put() to this channel a list of statements which,
   all together, translate into one or several commands.
   Currently, we support 2 types of commands:
   - 'table-name', {a Python dictionary which fits your database schema
     (keys of the dictionary being SQL column names)}
   - 'DBW_CALL_SQL_FUNCTION', 'sql_function_name', [list of parameters]
   """

   # TODO: since we INSERT a lot of records, check if pgloader is not
   # better <http://pgfoundry.org/projects/pgloader/>

   # Or the copy_from method of psycopg2, a psycopg extension (see
   # Using COPY TO and COPY FROM) in extensions.rst
   
   def __init__(self, id, db_conninfo, channel, autocommit=False):
       """ db_conninfo is a PostgreSQL conninfo
       <http://www.postgresql.org/docs/current/static/libpq-connect.html>,
       channel a Python Queue"""
       threading.Thread.__init__(self, name="Database writer %i" % id)
       self.connection = psycopg2.connect(db_conninfo)
       if autocommit:
           self.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
       self.cursor = self.connection.cursor ()
       self.cursor.execute("SET CLIENT_ENCODING='utf-8'")
       self.channel = channel
       
   def run(self):
       while True:
           parameters = self.channel.get()
           if parameters is None or len(parameters) == 0 or parameters[0] is None:
               if not self.channel.empty():
                   print  >>sys.stderr, \
                         "WARNING: database writer \"%s\" is going to shut down\n\t" + \
                         "but there are still %i entries in its input queue" % \
                         (self.getName(), self.channel.qsize())
               break
           while len(parameters) > 0 and parameters[0] is not None:
               
               if parameters[0] == 'DBW_CALL_SQL_FUNCTION' and len(parameters) >= 3:
                   func_name = parameters[1]
                   func_parameters = parameters[2]
                   parameters = parameters[3:]
                   self.cursor.callproc(func_name, func_parameters)
               else:
                   table_name = parameters[0]
                   namesandvalues = parameters[1]
                   parameters = parameters[2:]
                   placeholders = []
                   try:
                       names = namesandvalues.keys()
                   except AttributeError:
                       print  >>sys.stderr, "\nException Attribute Error (probably a bug in the protocol) in %s while getting keys: namesandvalues is \"%s\"" % (self.getName(), namesandvalues)
                       sys.exit(1)
                   names.sort()
                   for name in names:
                       placeholders.append("%%(%s)s" % name)
                   self.cursor.execute("""SELECT id FROM Zones WHERE name=%(domain)s AND uuid=%(uuid)s;""",
                                       namesandvalues)
                   result = self.cursor.fetchone()
                   if result is None:
                       raise Exception("No information about zone %s found in database" % namesandvalues["domain"])
                   if len(result) != 1:
                       raise Exception("More than one tuple about zone %s found in database" % namesandvalues["domain"])
                   zone_id = int(result[0])
                   namesandvalues["zone"] = zone_id
                   placeholders.append("%(zone)s")
                   command = """INSERT INTO %s (%s, zone)
                                            VALUES (%s);""" % (table_name, ",".join(names), ",".join(placeholders))
                   try:
                       self.cursor.execute(command, namesandvalues)
                   except psycopg2.DataError: # Data can be 8 bits and can be unsuitable for the database encoding
                       # TODO: receive a debug option and, if it is set, displays a warning
                       print >>sys.stderr, "Warning in %s: invalid data received for table %s: %s" % (self.getName(), table_name, namesandvalues)
                       pass # We just drop invalid data. TODO: does not work since the transaction is aborted
       self.connection.commit()
       self.cursor.close()
       self.connection.close()

class SharedDictionary:
    """
    A class to manage a shared dictionary between multiple threads or processes.
    It only provides 3 functions:
    - lock(key)
    - read_or_lock(key) -> lock, try to read and return value and (only if the value was found!) unlock.
    - write_and_unlock(key, value)
    /!\ Warning, if the stored value is None, we return str(None).
    """
    def __init__(self):
        self.main_lock = threading.Lock()
        self.dict_locks = {}
        self.d = {} # The true shared dictionary

    def lock (self, key):
        self.main_lock.acquire()
        try:
            self.dict_locks[key].acquire()
        except KeyError:
            self.dict_locks[key] = threading.Lock()
            self.dict_locks[key].acquire()
        finally:
            self.main_lock.release()
        return True

    def read_or_lock(self, key):
        self.lock(key)
        # we can now read safely
        try:
            r = self.d[key]
            self.dict_locks[key].release()
            if r is None:
                return str(None)
            return r
        except KeyError:
            return None # warning, d[key] is still locked!

    def write_and_unlock(self, key, value):
        self.d[key] = value
        self.dict_locks[key].release()

def make_resolver(addresses=None, size=edns_size):
    """ Creates a stub resolver which will use the IP addresses in the
        array "addresses" as full resolvers. """
    myresolver = dns.resolver.Resolver()
    if addresses is not None and addresses != []:
        myresolver.nameservers = addresses
    myresolver.use_edns(0, 0, size)
    return myresolver

def to_utf8(string):
    """ Try to convert a random string to utf-8 """
    if string is None:
        return None
    try:
        res = string.decode("utf-8")
    except UnicodeDecodeError:
        try:
            res = string.decode("ascii")
        except UnicodeDecodeError:
            res = string.decode("latin-1")
    return res

register_adapter(Inet, adapt_inet)
