# Copyright (C) 2005 Laurent A.V. Szyster
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

"http://laurentszyster.be/blog/async_server/"

import socket, time

from allegra import async_loop, async_core, async_limits


class Listen (async_core.Dispatcher):
        
        ac_in_meter = ac_out_meter = 0
        server_when = server_dispatched = 0
        
        def __init__ (
                self, Dispatcher, addr, precision, max, family
                ):
                self.server_dispatchers = []
                self.server_named = {}
                self.Server_dispatcher = Dispatcher
                self.server_precision = precision
                #
                async_core.Dispatcher.__init__ (self)
                self.create_socket (family, socket.SOCK_STREAM)
                self.set_reuse_addr ()
                self.bind (addr)
                self.listen (max)
                #
                anonymous (self)
                accept_all (self)
                metered (self)             
                #
                self.log ('listen', 'info')

        def __repr__ (self):
                return 'async-server id="%x"' % id (self)

        def readable (self):
                return self.accepting

        def writable (self):
                return False

        def handle_accept (self):
                try:
                        conn, addr = self.accept ()
                except socket.error:
                        assert None == self.log (
                                'accept-bogus-socket', 'error'
                                )
                        return
                        #
                        # Medusa original comments from Sam Rushing:
                        #
                        # linux: on rare occasions we get a bogus socket back 
                        # from accept. socketmodule.c:makesockaddr complains 
                        # that the address family is unknown. We don't want 
                        # the whole server to shut down because of this.
                
                except TypeError:
                        assert None == self.log (
                                'accept-would-block', 'error'
                                )
                        return
                        #
                        # Medusa original comments from Sam Rushing:
                        #
                        # unpack non-sequence.  this can happen when a read 
                        # event fires on a listening socket, but when we call 
                        # accept() we get EWOULDBLOCK, so dispatcher.accept() 
                        # returns None. Seen on FreeBSD3.

                name = self.server_resolved (addr)
                if name != None:
                        try:
                                self.server_named[name] += 1
                        except KeyError:
                                self.server_named[name] = 1
                        if self.server_accepted (conn, addr, name):
                                self.server_accept (
                                        conn, addr, name
                                        )
                        else:
                                conn.close ()
                        return
                
                if self.server_resolve == None:
                        self.server_unresolved (conn, addr)
                        conn.close ()
                        return
                        
                def resolve (name):
                        try:
                                self.server_named[name] += 1
                        except KeyError:
                                self.server_named[name] = 1
                        if name == None:
                                self.server_unresolved (conn, addr)
                                conn.close ()
                        elif self.server_accepted (conn, addr, name):
                                self.server_accept (
                                        conn, addr, name
                                        )
                self.server_resolve (addr, resolve)
                        
        def handle_close (self):
                "close all dispatchers, close the server and finalize it"
                for dispatcher in tuple (self.server_dispatchers):
                        dispatcher.handle_close ()
                self.server_stop (time.time ())
                self.close ()
                self.__dict__ = {}
                #
                # Breaks any circular reference through attributes, by 
                # clearing them all. Note that this prevents finalizations
                # to be used with listeners, but anyway subclassing the
                # stop and shutdown methods provides enough leverage to
                # gracefully come to closure: the listener is most probably 
                # in the highest level of the application's instance tree.
                #
                # ... and sometimes damn hard to finalize ;-)
                
        def server_unresolved (self, conn, addr):
                assert None == self.log ('unresolved %r' % (addr,), 'debug')

        def server_accept (self, conn, addr, name):
                assert None == self.log ('accepted %r' % (addr,), 'debug')
                now = time.time ()
                dispatcher = self.Server_dispatcher (conn)
                dispatcher.addr = addr #?
                dispatcher.server_name = name
                dispatcher.server_when = now
                dispatcher.async_server = self
                self.server_decorate (dispatcher, now)
                if self.server_when == 0:
                        self.server_start (now)
                self.server_dispatchers.append (dispatcher)
                return dispatcher
                
        def server_start (self, when):
                "handle the client management startup"
                self.server_when = when
                async_loop.schedule (
                        when + self.server_precision, self.server_manage
                        )
                assert None == self.log ('start', 'debug')
                  
        def server_manage (self, when):
                if not self.server_dispatchers:
                        if self.accepting:
                                self.server_stop (when)
                        else:
                                self.handle_close ()
                        return
                
                if self.server_limit != None:
                        for dispatcher in tuple (self.server_dispatchers):
                                if self.server_limit (dispatcher, when):
                                        self.server_overflow (dispatcher)
                return (when + self.server_precision, self.server_manage)
        
        def server_overflow (self, dispatcher):
                "assert debug log and close an overflowed dispatcher"
                assert None == dispatcher.log ('limit overflow', 'debug')
                dispatcher.handle_close ()
                  
        def server_meter (self, dispatcher):
                "assert debug log and account I/O meters of a dispatcher"
                assert None == dispatcher.log (
                        'in="%d" out="%d"' % (
                                dispatcher.ac_in_meter, 
                                dispatcher.ac_out_meter
                                ),  'debug'
                        )
                self.ac_in_meter += dispatcher.ac_in_meter
                self.ac_out_meter += dispatcher.ac_out_meter
                self.server_dispatched += 1

        def server_close (self, dispatcher):
                "remove the dispatcher from list and meter dispatched"
                name = dispatcher.server_name
                if self.server_named[name] > 1:
                        self.server_named[name] -= 1
                else:
                        del self.server_named[name]
                self.server_dispatchers.remove (dispatcher)
                self.server_meter (dispatcher)
                dispatcher.async_server = None
                
        def server_stop (self, when):
                "handle the server scheduled or inpromptu stop"
                assert None == self.log (
                        'stop dispatched="%d"'
                        ' seconds="%f" in="%d" out="%d"' % (
                                self.server_dispatched,
                                (when - self.server_when),
                                self.ac_in_meter,
                                self.ac_out_meter
                                ), 'debug')
                self.server_when = self.server_dispatched = \
                        self.ac_in_meter = self.ac_out_meter = 0

        def server_shutdown (self):
                "stop accepting connections, close all current when done"
                assert None == self.log ('shutdown', 'debug')
                self.accepting = False                       
                for dispatcher in tuple (self.server_dispatchers):
                        dispatcher.close_when_done ()
                #if not self.server_dispatchers:
                #        self.handle_close ()
                return True
                        

def anonymous (server):
        "allways resolved to the empty string"
        server.server_resolved = (lambda addr: '')
        server.server_resolve = None
        return server

def accept_all (server):
        server.server_accepted = (lambda conn, addr, name: True)
        return server

def accept_named (listen, limit):
        def accepted (conn, addr, name):
                if listen.server_named[name] <= limit:
                        return True
                
                if listen.server_named[name] > 1:
                        listen.server_named[name] -= 1
                else:
                        del listen.server_named[name]
                assert None == listen.log (
                        'accept-limit ip="%s"' % name,
                        'error'
                        )
                return False
        
        listen.server_accepted = accepted 
        return listen

def unmeter (dispatcher):
        "remove stream decorators from a server dispatcher"
        del (
                dispatcher.recv, 
                dispatcher.send, 
                dispatcher.handle_close
                )

def meter (dispatcher, when):
        "decorate a server dispatcher with stream meters"
        async_limits.meter_recv (dispatcher, when)
        async_limits.meter_send (dispatcher, when)
        def handle_close ():
                unmeter (dispatcher)
                dispatcher.handle_close ()
                dispatcher.async_server.server_close (dispatcher)
                
        dispatcher.handle_close = handle_close

def metered (server, timeout=1<<32):
        "meter I/O for server streams"
        def decorate (dispatcher, when):
                meter (dispatcher, when)
                dispatcher.limit_inactive = timeout
                
        server.server_decorate = decorate
        server.server_inactive = timeout
        server.server_limit = None
        return server


def inactive (server, timeout):
        "meter I/O and limit inactivity for server streams"
        def decorate (dispatcher, when):
                meter (dispatcher, when)
                dispatcher.limit_inactive = server.server_inactive
                
        server.server_decorate = decorate
        server.server_inactive = timeout
        server.server_limit = async_limits.inactive
        return server


def limited (server, timeout, inBps, outBps):
        "throttle I/O and limit inactivity for managed client streams"
        def unthrottle (dispatcher):
                "remove limit decorators from a client dispatcher"
                del (
                        dispatcher.recv, 
                        dispatcher.send, 
                        dispatcher.readable,
                        dispatcher.writable,
                        dispatcher.handle_close
                        )
                
        def throttle (dispatcher, when):
                "decorate a client dispatcher with stream limits"
                async_limits.meter_recv (dispatcher, when)
                async_limits.meter_send (dispatcher, when)
                dispatcher.limit_inactive = timeout
                async_limits.throttle_readable (
                        dispatcher, when, server.ac_in_throttle_Bps
                        )
                async_limits.throttle_writable (
                        dispatcher, when, server.ac_out_throttle_Bps
                        )
                def handle_close ():
                        assert None == dispatcher.log (
                                'in="%d" out="%d"' % (
                                        dispatcher.ac_in_meter, 
                                        dispatcher.ac_out_meter
                                        ),  'debug'
                                )
                        unthrottle (dispatcher)
                        dispatcher.handle_close ()
                        dispatcher.async_server.server_close (dispatcher)
                        
                dispatcher.handle_close = handle_close

        server.server_decorate = throttle
        server.ac_in_throttle_Bps = inBps
        server.ac_out_throttle_Bps = outBps
        server.server_limit = async_limits.limit
        return server


def rationed (server, timeout, inBps, outBps):
        "ration I/O and limit inactivity for managed client streams"
        server.ac_in_ration_Bps = inBps
        server.ac_out_ration_Bps = outBps
        def throttle_in ():
                return int (server.ac_in_ration_Bps / max (len (
                        server.server_dispatchers
                        ), 1))

        def throttle_out ():
                return int (server.ac_out_ration_Bps / max (len (
                        server.server_dispatchers
                        ), 1))

        limited (server, timeout, throttle_in, throttle_out)
        return server
        