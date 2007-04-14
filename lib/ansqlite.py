# Copyright (C) 2007 Laurent A.V. Szyster
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
#    http://www.gnu.org/copyleft/gpl.html
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

"http://laurentszyster.be/blog/ansqlite/"

import collections
from cPickle import dumps, loads
try:
        import sqlite
except:
        from pysqlite2 import dbapi2 as sqlite

from allegra import loginfo, async_net, tcp_client


class Client (async_net.Dispatcher):

        def __init__ (self):
                async_net.Dispatcher.__init__ (self)
                self.sql_defered = collections.deque ()
        
        def async_net_continue (self, data):
                try:
                        self.sql_defered.popleft () (loads (data))
                except:
                        self.loginfo_traceback ()
                
        def handle_close (self):
                self.close ()
                while self.sql_defered:
                        self.async_net_continue ('N.')


class Proxy (object):
        
        def __init__ (self, dispatcher):
                self.output_fifo, self.sql_defered = (
                        dispatcher.output_fifo, dispatcher.sql_defered
                        )
                        
        def __call__ (self, callback, statement, params=()):
                s = dumps ((statement.lstrip (), params))
                self.output_fifo.append ('%d:%s,' % (len (s), s))
                self.sql_defered.append (callback)
                
        def reconnect (self, name, finalize, timeout=3.0):
                dispatcher = Client ()
                dispatcher.finalization = finalize
                if tcp_client.connect (dispatcher, name, timeout):
                        self.__init__ (dispatcher)
                

def connect (name, finalize, timeout=3.0):
        dispatcher = Client ()
        dispatcher.finalization = finalize
        if tcp_client.connect (dispatcher, name, timeout=3.0):
                return Proxy (dispatcher)
        

class Server (async_net.Dispatcher):
        
        def async_net_continue (self, data):
                try:
                        statement, params = loads (data)
                        s = dumps (
                                self.ansqlite (statement, params).fetchall ()
                                ) # ansqlite is not a bounded method!
                except sqlite.DatabaseError, e:
                        s = dumps (e.args[0])
                except:
                        self.loginfo_traceback ()
                        s = 'N.' # None
                else:
                        if statement[:6].upper() != 'SELECT':
                                loginfo.log (data)
                self.output_fifo.append ('%d:%s,' % (len (s), s))


def decorate (Class, conn):
        "factor a handler for ansqlite.Server from an SQLite connection"
        def handle (statement, params):
                if params == (): # a single statement
                        return conn.execute (statement)
                
                elif params == None: # a batch of SQL statements
                        return conn.executescript (statement)
                
                elif type (params[0]) == tuple: # many prepared statements
                        return conn.executemany (statement, params)
                                
                else: # a single prepared statement
                        return conn.execute (statement, params)
                                
        Class.ansqlite = staticmethod (handle)
        return Class


"""

<h3>Synopsis</h3>

<p>This module provides a class to connect asynchronous SQL clients and 
servers written in Python over a TCP/IP stream of netstrings. This file is 
both a library module, an application script and as such a partial test unit 
of the implementation.</p>

<p>Here, definitively, less is so much more.</p>

<p>...

<pre>python -OO lib/ansqlite.py 127.0.0.1:2345 data/my.db \
    1> log/my.out 2> log/my.err</pre>
    
...

<pre>python -OO lib/ansqlite.py 127.0.0.1:2345 :memory: \
    1> log/my.out 2> log/my.err</pre>
    
<pre>python -OO lib/ansqlite.py 127.0.0.1:2345 :memory: \
    < data/my.in 1> log/my.out 2> log/my.err</pre>
    
...

<h4>Client</h4>

<p>...

<pre>from allegra import async_client, ansqlite
sql = ansqlite.Client ()
if async_client.connect (sql, ('127.0.0.1', 3536)):
    def callback (result): 
        loginfo.log('%r' % result) # log the result list, error or None.

    sql (callback, '...') # execute
    sql (callback, '...', (1,2,3)) # execute
    sql (callback, '...', ((1,2,3), (4,5,6))) # executemany
    sql (callback, '...', None) # executescript</pre>

...</p>

<h4>Server</h4>

<p>...

<pre>from pysqlite2 import dbapi2
from allegra import async_loop, async_server, ansqlite

Class MySQLite (ansqlite.Server):
    MySQLite.database = dbapi2.connect (":memory:")

async_loop.catch (async_server.Listen (
    MySQLite, ("127.0.0.1", 3536), precision=3.0, max=5
    ).server_shutdown)

async_loop.dispatch ()</pre>

...</p>


Applications

Any database network application that must scale up, ie: where agent states
are distributed on network peers and the global state is partitionned in 
independant processes as databases.

The benefit of an asynchronous API for a two-tier architecture is to
allow consolidation by database applications and distribution of the 
network of database applications on a grid of commodity computers.

Cheap PCs and Debian GNU/Linux to host HTTP agents with no moving parts, 
IBM and Novell's S/390 Linux to run your databases in independant processes 
and managed VMs. And anything in between that supports CPython 2.4 or newer.

At C speed and with Python's reliability ;-)


Note about this implementation

That one I'll comment, for whoever reads this but me.

Here's an Asynchronous Netstring SQLite server in less than 150 lines of 
sources code, comments and licences included. Complete with a client 
dispatcher, a server listener and a high performance server that handles 
SELECT, INSERT and UPDATE at an allmost constant rate of one request every 
3ms on a 1.7Ghz laptop. And support for BLOBS.

YMMV, but remember that this asynchronous network SQL server handles high 
contention and latency without effort, scaling up to high availability.

Of course to achieve that constant high performance, SQLite must load all 
the database in memory and let the network peer log its output. This is 
precisely why, when testing both the client and the server on the same 
Windows XP laptop the time per transaction is allmost constant, although 
the tests select more than they insert or update. Because on this hardware 
and with this OS and CPython VM, commiting to the log file takes a lot 
longer than querying ten or hundred lines, updating or inserting one or ten
rows ... in memory. 

At full C speed, in memory and with native binding, the SQLite engine and 
Python's cPickle serialization library guarantee the fastest possible way
to query or update an SQL database over the network. And with asynchronous
client and server, ansqlite's connections avoid contention and latency
issues that plague synchronous designs (J2EE and LAMP).

The only performance tuning to do for ansqlite is to commit log to 
persistence as fast as possible on a given system, the rest is optimal. 

"""