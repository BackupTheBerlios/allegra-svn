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
                self.pipeline_responses = collections.deque ()
                pipelined_requests = 0
                
        def __call__ (self, callback, statement, params=()):
                s = dumps ((statement, params))
                self.output_fifo.append ('%d:%s,' % (len (s), s))
                self.pipeline_responses.append (callback)
                self.pipelined_requests += 1
                
        def prepared (self, callback, prepared, params=()):
                s = dumps (params)
                self.output_fifo.append ('%d:[%s,%s],' % (
                        len (s) + len (prepared) + 3, prepared, s
                        ))
                self.pipeline_responses.append (callback)
                self.pipelined_requests += 1

        def encoded (self, callback, encoded):
                self.output_fifo.append ('%d:%s,' % (len (encoded), encoded))
                self.pipeline_responses.append (callback)
                self.pipelined_requests += 1

        def async_net_continue (self, data):
                try:
                        self.pipeline_responses.popleft () (data)
                except:
                        self.loginfo_traceback ()
                        

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
        def execute (statement, parameters):
                if parameters == None:
                        return [i[0] for i in (
                                sql1 (statement).description or ()
                                )] # eventually list column names
                        
                elif len (parameters) > 0 and (
                        type (parameters[0]) in bindings
                        ):
                        return sqlM (statement, parameters).fetchall()

                return sql1 (statement, parameters).fetchall()
                
        def ansql (statement, parameters):
                if type (statement) == unicode:
                        return execute (statement, parameters)

                results = []
                push = results.append
                sql1 (u"BEGIN")
                try:
                        for s, p in zip (statement, parameters):
                                push (execute (s, p))
                except sqlite.Error, e:
                        sql1 (u"ROLLBACK")
                        push (str (e.args[0]))
                except:
                        sql1 (u"ROLLBACK")
                        push (u"ansqlite protocol error")
                else:
                        sql1 (u"COMMIT")
                return results

        class Dispatcher (Base):
                def async_net_continue (self, data):
                        try:
                                statement, params = loads (data)
                                s = dumps (self.ansql (statement, params)) 
                        except sqlite.Error, e:
                                self.loginfo_traceback ()
                                s = dumps (e.args[0])
                        except:
                                self.loginfo_traceback ()
                                s = dumps (u"ansqlite protocol error")
                        else:
                                if statement[:6].upper() != 'SELECT':
                                        loginfo.log (data)
                        self.output_fifo.append ('%d:%s,' % (len (s), s))
        
        Dispatcher.ansql = staticmethod (ansql)
        return conn, Dispatcher