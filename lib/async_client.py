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

""

import time, socket, collections

from allegra import loginfo, async_loop, async_limits
        

# a pipeline mix-in

class Pipeline (object):
        
        "a pipeline mix-in for dispatcher"

        pipeline_sleeping = False
        pipeline_keep_alive = False

        def __init__ (self, requests=None, responses=None):
                self.pipeline_requests = requests or collections.deque ()
                self.pipeline_responses = responses or collections.deque ()

        def pipeline (self, request):
                self.pipeline_requests.append (request)
                if self.pipeline_sleeping:
                        self.pipeline_sleeping = False
                        self.pipeline_wake_up ()

        def pipeline_wake_up (self):
                # pipelining protocols, like HTTP/1.1 or ESMPT
                requests = self.pipeline_requests
                if self.pipeline_requests:
                        while self.pipeline_requests:
                                reactor = self.pipeline_requests.popleft ()
                                self.pipeline_push (reactor)
                                self.pipeline_responses.append (reactor)
                self.pipeline_sleeping = True

        def pipeline_wake_up_once (self):
                # synchronous protocols, like HTTP/1.0 or SMTP
                if self.pipeline_requests:
                        reactor = self.pipeline_requests.popleft ()
                        self.pipeline_push (reactor)
                        self.pipeline_responses.append (reactor)
                        self.pipeline_sleeping = False
                else:
                        self.pipeline_sleeping = True
                        
        def pipeline_push (self, reactor):
                assert None == loginfo.log (
                        '%r' % reactor, 'pipeline_push'
                        )

class Dispatcher (object):
        
        "client mix-in for stream dispatcher"
        
        client_when = 0

        def client_connect (self, addr, timeout, family=socket.AF_INET):
                "create a socket, try to connect it and schedule a timeout"
                assert not self.connected and self.socket == None
                try:
                        self.create_socket (family, socket.SOCK_STREAM)
                        self.connect (addr)
                except:
                        self.loginfo_traceback ()
                        return False
                        
                assert None == self.log ('connect', 'debug')
                self.client_when = time.time ()
                async_loop.async_schedule (
                        self.client_when + timeout, self.client_timeout
                        )
                return True

        def client_timeout (self, when):
                "if not connected and not closing yet, handle close"
                if not self.connected and not self.closing:
                        assert None == self.log (
                                'connect-timeout %f seconds' % (
                                        when - self.client_when
                                        ), 'debug'
                                )
                        self.handle_close ()

# A manager abstraction for limited client dispatchers

class Manager (loginfo.Loginfo):
        
        "a connection manager base abstraction for dispatcher"

        ac_in_meter = ac_out_meter = 0
        client_when = client_dispatched = 0
        
        def __init__ (self, timeout, precision, family=socket.AF_INET):
                "initialize a new client manager"
                self.client_managed = {}
                self.client_timeout = timeout
                self.client_precision = precision
                self.client_family = family
                resolved (self)
                inactive (self, timeout)
                
        def __call__ (self, dispatcher, name):
                now = time.time ()
                dispatcher.client_manager = self
                self.client_decorate (dispatcher, now)
                key = id (dispatcher)
                self.client_managed[key] = dispatcher
                dispatcher.client_key = key
                if len (self.client_managed) == 1:
                        self.client_start (now)
                self.client_connect (dispatcher, name)
                return dispatcher
                
        def client_connect (self, dispatcher, name):
                if self.client_resolved (name):
                        if not dispatcher.client_connect (
                                name, self.client_timeout,
                                self.client_family
                                ):
                                dispatcher.handle_close ()
                        return

                assert self.client_resolve != None
                def resolve (addr):
                        if (
                                addr == None or not
                                dispatcher.client_connect (
                                        addr, self.client_timeout,
                                        self.client_family
                                        )
                                ):
                                dispatcher.handle_close ()
                self.client_resolve (name, resolve)

        def client_start (self, when):
                "handle the client management startup"
                self.client_when = when
                async_loop.async_schedule (
                        when + self.client_precision, self.client_manage
                        )
                assert None == self.log ('start', 'debug')

        def client_manage (self, when):
                "test limits overflow, recure or stop"
                for dispatcher in self.client_dispatchers ():
                        if self.client_limit (dispatcher, when):
                                self.client_overflow (dispatcher)
                if self.client_managed:
                        return (
                                when + self.client_precision,
                                self.client_manage
                                ) # continue to defer
                
                self.client_stop (when)
                return None
        
        def client_dispatchers (self):
                return self.client_managed.values ()
                        
        def client_overflow (self, dispatcher):
                "assert debug log and close an overflowed dispatcher"
                assert None == dispatcher.log ('limit overflow', 'debug')
                dispatcher.handle_close ()

        def client_close (self, dispatcher):
                "remove the dispatcher from cache and increment dispatched"
                self.client_dispatched += 1
                del self.client_managed[dispatcher.client_key]
                dispatcher.client_manager = None

        def client_stop (self, when):
                "handle the client management stop"
                assert None == self.log (
                        'stop dispatched="%d"'
                        ' seconds="%f" in="%d" out="%d"' % (
                                self.client_dispatched,
                                (when - self.client_when),
                                self.ac_in_meter,
                                self.ac_out_meter
                                ), 'debug')

        def client_shutdown (self):
                "close all client dispatchers when done"
                for dispatcher in self.client_dispatchers ():
                        dispatcher.close_when_done ()
                        

class Cache (Manager):

        def __init__ (self, timeout, precision, family=socket.AF_INET):
                self.client_managed = {}
                self.client_timeout = timeout
                self.client_precision = precision
                self.client_family = family
                resolved (self)
                inactive (self, timeout)
                
        def __call__ (self, Dispatcher, name):
                """return a cached or a new dispatcher, maybe resolving and
                connecting it first, closing it on connection error or if
                it's socket address cannot be resolved"""
                try:
                        return self.client_managed[name]
                        
                except KeyError:
                        pass
                now = time.time ()
                dispatcher = Dispatcher ()
                dispatcher.client_manager = self
                self.client_decorate (dispatcher, now)
                self.client_managed[name] = dispatcher
                dispatcher.client_key = name
                self.client_connect (dispatcher, name)
                if len (self.client_managed) == 1:
                        self.client_start (now)
                return dispatcher


class Pool (Manager):
        
        def __init__ (
                self, Dispatcher, name, pool, timeout, precision, 
                family=socket.AF_INET
                ):
                assert pool > 1
                self.client_managed = []
                self.client_pool = pool
                self.client_name = name
                self.client_called = 0
                self.Client_dispatcher = Dispatcher
                self.client_timeout = timeout
                self.client_precision = precision
                self.client_family = family
                resolved (self)
                inactive (self, timeout)
                
        def __call__ (self):
                size = len (self.client_managed)
                if size == self.client_pool:
                        self.client_called += 1
                        return self.client_managed[self.client_called % size]
                
                now = time.time ()
                dispatcher = self.Client_dispatcher ()
                dispatcher.client_manager = self
                self.client_decorate (dispatcher, now)
                self.client_managed.append (dispatcher)
                self.client_connect (dispatcher, self.client_name)
                if len (self.client_managed) == 1:
                        self.client_start (now)
                return dispatcher

        def client_dispatchers (self):
                return list (self.client_managed)
                        
        def client_close (self, dispatcher):
                "remove the dispatcher from pool and increment dispatched"
                self.client_dispatched += 1
                self.client_managed.remove (dispatcher)
                dispatcher.client_manager = None


# unresolved name

def resolved (manager):
        "allways resolved for unresolved dispatcher address"
        manager.client_resolved = (lambda name: True)
        manager.client_resolve = None


# metered I/O with inactive limit

def unmeter (dispatcher):
        "remove stream decorators from a client dispatcher"
        (
                dispatcher.recv, 
                dispatcher.send, 
                dispatcher.handle_close
                ) = dispatcher.client_decorated
        dispatcher.client_decorated = None

def meter (dispatcher, when):
        "decorate a client dispatcher with stream meters"
        dispatcher.client_decorated = (
                dispatcher.recv, 
                dispatcher.send, 
                dispatcher.handle_close
                )
        async_limits.meter_recv (dispatcher, when)
        async_limits.meter_send (dispatcher, when)
        def handle_close ():
                assert None == dispatcher.log (
                        'in="%d" out="%d"' % (
                                dispatcher.ac_in_meter, 
                                dispatcher.ac_out_meter
                                ),  'debug'
                        )
                unmeter (dispatcher)
                dispatcher.handle_close ()
                manager = dispatcher.client_manager
                manager.ac_in_meter += dispatcher.ac_in_meter
                manager.ac_out_meter += dispatcher.ac_out_meter
                manager.client_close (dispatcher)
                
        dispatcher.handle_close = handle_close

def inactive (manager, timeout):
        "meter I/O and limit inactivity for client streams"
        def decorate (dispatcher, when):
                meter (dispatcher, when)
                dispatcher.limit_inactive = timeout
                
        manager.client_decorate = decorate
        manager.client_limit = async_limits.inactive


# metered and throttled I/O with inactive limit

def limited (manager, timeout, inBps, outBps):
        "throttle I/O and limit inactivity for client streams"
        def unthrottle (dispatcher):
                "remove limit decorators from a client dispatcher"
                (
                        dispatcher.recv, 
                        dispatcher.send, 
                        dispatcher.readable,
                        dispatcher.writable,
                        dispatcher.handle_close
                        ) = dispatcher.client_decorated
                dispatcher.client_decorated = None
                
        def throttle (dispatcher, when):
                "decorate a client dispatcher with stream limits"
                dispatcher.client_decorated = (
                        dispatcher.recv, 
                        dispatcher.send, 
                        dispatcher.readable,
                        dispatcher.writable,
                        dispatcher.handle_close
                        )
                async_limits.meter_recv (dispatcher, when)
                async_limits.meter_send (dispatcher, when)
                dispatcher.limit_inactive = timeout
                async_limits.throttle_readable (dispatcher, when, inBps)
                async_limits.throttle_writable (dispatcher, when, outBps)
                def handle_close ():
                        assert None == dispatcher.log (
                                'in="%d" out="%d"' % (
                                        dispatcher.ac_in_meter, 
                                        dispatcher.ac_out_meter
                                        ),  'debug'
                                )
                        unthrottle (dispatcher)
                        dispatcher.handle_close ()
                        m = dispatcher.client_manager
                        m.ac_in_meter += dispatcher.ac_in_meter
                        m.ac_out_meter += dispatcher.ac_out_meter
                        m.client_close (dispatcher)
                        
                dispatcher.handle_close = handle_close

        manager.client_decorate = throttle
        manager.client_limit = async_limits.limit


# metered and rationated I/O with inactive limit

def rationed (manager, timeout, inBps, outBps):
        manager.ac_in_throttle_Bps = inBps
        manager.ac_out_throttle_Bps = outBps
        def throttle_in ():
                return int (manager.ac_in_throttle_Bps / max (len (
                        manager.client_managed
                        ), 1))

        def throttle_out ():
                return int (manager.ac_out_throttle_Bps / max (len (
                        manager.client_managed
                        ), 1))

        limited (manager, timeout, throttle_in, throttle_out)
