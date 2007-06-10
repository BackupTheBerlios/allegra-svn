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
try: # try JSON-The-Model ...
        import cjson  
        json_decode = cjson.decode
        loads = (lambda s: json_decode (s, 1)) # ... and use UNICODE only ...
        dumps = cjson.encode
except:  # ... or fail over to CPython only encoding
        from cPickle import loads, dumps

from allegra import netstring, loginfo, async_net, tcp_client


class Client (async_net.Dispatcher):
        """
        from allegra import async_loop, tcp_client, ansqlite

        ansql = ansqlite.Client ()
        callback = (lambda response: 
            ansql.log (ansqlite.loads (response)))
        if tcp_client.connect (ansql, ('127.0.0.2', 3999)):
            ansql (callback, u"SELECT ...")
        async_loop.dispatch ()
        """
        def __init__ (self):
                async_net.Dispatcher.__init__ (self)
                self.callbacks = collections.deque ()
                
        def __call__ (self, callback, statement, params=()):
                s = dumps ((statement, params))
                self.output_fifo.append ('%d:%s,' % (len (s), s))
                self.callbacks.append (callback)
                
        def json (self, callback, prepared, params=()):
                s = dumps (params)
                self.output_fifo.append ('%d:[%s,%s],' % (
                        len (s) + len (prepared) + 3, prepared, s
                        ))
                self.callbacks.append (callback)

        def async_net_continue (self, data):
                try:
                        self.callbacks.popleft () (data)
                except:
                        self.loginfo_traceback ()
                        

def connect (name, timeout=3.0):
        sql = Client ()
        if not tcp_client.connect (sql, name, timeout):
               return sql
       
        def finalize (dispatcher):
                while dispatcher.sql_defered:
                        try:
                                dispatcher.callbacks.popleft () (None)
                        except:
                                dispatcher.loginfo_traceback ()

        sql.finalization = finalize


def open (database, Base=async_net.Dispatcher):
        """
        from allegra import async_loop, tcp_server, ansqlite

        conn, Dispatcher = ansqlite.open (":memory:")
        try:
            async_loop.catch (tcp_server.Listen (
                ansqlite.Dispatcher, ('127.0.0.2', 3999), 1.0
                ).server_shutdown)
            async_loop.dispatch ()
        finally:
            conn.close ()
        """
        try:
                import sqlite
                bindings = (list, tuple, dict)
        except:
                from pysqlite2 import dbapi2 as sqlite
                bindings = (list, tuple)
                
        conn = sqlite.connect (database, check_same_thread=False)
        sql1 = conn.execute 
        sqlM = conn.executemany
        def ansql (statement, parameters):
                if type (statement) == unicode:
                        if parameters == None:
                                return [i[0] for i in (
                                        sql1 (statement).description or ()
                                        )] # eventually list column names
                                
                        if len (parameters) > 0 and (
                                type (parameters[0]) in bindings
                                ):
                                return sqlM (statement, parameters).fetchall()
        
                        else:
                                return sql1 (statement, parameters).fetchall()
                else: 
                        # ODBC/JDBC batches, done asynchronously ACID!
                        results = []
                        push = results.append 
                        try:
                                # push all results ...
                                for s, p in zip (statement, parameters):
                                        if p == None:
                                                push ([meta[0] for meta in (
                                                        sql1 (s).description 
                                                        or ())])
                                        elif len (p) > 0 and (
                                                type (p[0]) in bindings
                                                ):
                                                push (sqlM (s, p).fetchall())
                                        else:
                                                push (sql1 (s, p).fetchall())
                        except: # stop on exception and rollback
                                sql1 ('ROLLBACK')
                                push (False)
                        else: #  commit transaction without error
                                sql1 ('COMMIT')
                                push (True)
                        return results # ... results[-1] == success | failure

        class Dispatcher (Base):
                def async_net_continue (self, data):
                        try:
                                statement, params = loads (data)
                                s = dumps (self.ansql (statement, params)) 
                        except self.SQLiteError, e:
                                self.loginfo_traceback ()
                                s = dumps (e.args[0])
                        except:
                                self.loginfo_traceback ()
                                s = dumps ("ansqlite exception")
                        else:
                                if statement[:6].upper() != 'SELECT':
                                        loginfo.log (data)
                        self.output_fifo.append ('%d:%s,' % (len (s), s))
        
        Dispatcher.SQLiteError = sqlite.Error
        Dispatcher.ansql = staticmethod (ansql)
        return conn, Dispatcher