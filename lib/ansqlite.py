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