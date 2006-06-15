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

# A manager abstraction for limited client dispatchers

UNRESOLVED = ((lambda key: True), None)

def nolimit (dispatcher, when):
        "dummy limit for unlimited dispatcher"
        return False

def unmanaged (dispatcher):
        "remove the handle_close decorator from  a client dispatcher"
        dispatcher.handle_close = dispatcher.client_decorated
        dispatcher.client_decorated = None

def managed (dispatcher, when):
        "decorate a client dispatcher's handle_close method"
        dispatcher.client_decorated = dispatcher.handle_close
        def handle_close ():
                unmanaged (dispatcher)
                dispatcher.handle_close ()
                dispatcher.client_manager.client_close (dispatcher)
                
        dispatcher.handle_close = handle_close

UNLIMITED = (managed, nolimit)


class Manager (loginfo.Loginfo):
        
        client_when = client_dispatched = 0
        
        def __init__ (
                self, Dispatcher, 
                timeout=60, precision=6, 
                limits=UNLIMITED, resolution=UNRESOLVED,
                family=socket.AF_INET 
                ):
                "initialize a new client manager"
                self.client_dispatchers = {}
                self.Client_dispatcher = Dispatcher
                self.client_family = family
                self.client_timeout = timeout
                self.client_precision = precision
                self.client_decorate, self.client_limit = limits
                self.client_resolved, self.client_resolve = resolution
                        
        def client_dispatcher (self, key):
                """return a cached or a new dispatcher, maybe resolving and
                connecting it first, closing it on connection error or if
                it's socket address cannot be resolved"""
                try:
                        return self.client_dispatchers[key]
                        
                except KeyError:
                        pass
                now = time.time ()
                dispatcher = self.Client_dispatcher ()
                dispatcher.client_key = key
                dispatcher.client_manager = self
                self.client_decorate (dispatcher, now)
                self.client_dispatchers[key] = dispatcher
                if self.client_resolved (key):
                        if not dispatcher.client_connect (
                                key, self.client_timeout,
                                self.client_family
                                ):
                                dispatcher.handle_close ()
                        if len (self.client_dispatchers) == 1:
                                self.client_start (now)
                        return dispatcher

                assert self.client_resolve != None
                if len (self.client_dispatchers) == 1:
                        self.client_start (now)
                def resolve (addr):
                        if (
                                addr == None or not
                                dispatcher.client_connect (
                                        addr, self.client_timeout,
                                        self.client_family
                                        )
                                ):
                                dispatcher.handle_close ()
                self.client_resolve (key, resolve)
                return dispatcher

        __call__ = client_dispatcher
                
        def client_start (self, when):
                "handle the client management startup"
                self.client_when = when
                async_loop.async_schedule (
                        when + self.client_precision, self.client_manage
                        )
                assert None == self.log ('start', 'debug')

        def client_manage (self, when):
                "test limits overflow, recure or stop"
                for dispatcher in self.client_dispatchers.values ():
                        if self.client_limit (dispatcher, when):
                                self.client_overflow (dispatcher)
                if self.client_dispatchers:
                        return (
                                when + self.client_precision,
                                self.client_manage
                                ) # continue to defer
                
                self.client_stop (when)
                return None
        
        def client_overflow (self, dispatcher):
                "assert debug log and close an overflowed dispatcher"
                assert None == dispatcher.log ('limit overflow', 'debug')
                dispatcher.handle_close ()

        def client_close (self, dispatcher):
                "remove the dispatcher from cache and increment dispatched"
                self.client_dispatched += 1
                del self.client_dispatchers[dispatcher.client_key]
                dispatcher.client_manager = None
                                
        def client_stop (self, when):
                "handle the client management stop"
                assert None == self.log ('stop %f sec' % (
                        when - self.client_when
                        ), 'debug')

        def client_shutdown (self):
                "close all client dispatchers when done"
                for dispatcher in self.client_dispatchers.values ():
                        dispatcher.close_when_done ()
          
# unmetered and unlimited              

def unlimited (client):
        "unmeter and unlimit I/O"
        client.client_decorate = managed
        client.client_limit = nolimit
        
# metered I/O

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
                manager.client_bytes_in += dispatcher.ac_in_meter
                manager.client_bytes_out += dispatcher.ac_out_meter
                manager.client_close (dispatcher)
                
        dispatcher.handle_close = handle_close

def metered (client):
        client.client_bytes_in = client.client_bytes_out = 0
        client.client_decorate = meter
        client.client_limit = nolimit


# metered I/O with inactive limit

def inactive (client, timeout):
        "meter I/O and limit inactivity for client streams"
        def decorate (dispatcher, when):
                meter (dispatcher, when)
                dispatcher.limit_inactive = timeout
                
        client.client_bytes_in = client.client_bytes_out = 0
        client.client_decorate = decorate
        client.client_limit = async_limits.inactive


# metered and throttled I/O with inactive limit

def limited (client, timeout, inBps, outBps):
        "throttle I/O and limit inactivity for client streams"
        def undecorate (dispatcher):
                "remove limit decorators from a client dispatcher"
                (
                        dispatcher.recv, 
                        dispatcher.send, 
                        dispatcher.readable,
                        dispatcher.writable,
                        dispatcher.handle_close
                        ) = dispatcher.client_decorated
                dispatcher.client_decorated = None
        
        def decorate (dispatcher, when):
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
                        undecorate (dispatcher)
                        dispatcher.handle_close ()
                        manager = dispatcher.client_manager
                        manager.client_bytes_in += dispatcher.ac_in_meter
                        manager.client_bytes_out += dispatcher.ac_out_meter
                        manager.client_close (dispatcher)
                        
                dispatcher.handle_close = handle_close
        
        client.client_bytes_in = client.client_bytes_out = 0
        client.client_decorate = decorate
        client.client_limit = async_limits.limit


# metered and rationated I/O with inactive limit

def rationated (client, timeout, inBps, outBps):
        dispatchers = client.client_dispatchers
        limited (
                client, timeout, 
                (lambda: int (inBps ()/len (dispatchers))),
                (lambda: int (outBps ()/len (dispatchers)))
                )
