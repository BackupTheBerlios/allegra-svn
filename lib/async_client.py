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
        
        "client mix-in for SOCK_STREAM dispatcher"
        
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


class Manager (loginfo.Loginfo):
        
        "a connection manager for async_client.Dispatcher instances"

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
                        if addr == None:
                                self.client_unresolved (dispatcher, name)
                        elif not dispatcher.client_connect (
                                addr, self.client_timeout,
                                self.client_family
                                ):
                                dispatcher.handle_close ()
                self.client_resolve (name, resolve)
                
        def client_unresolved (self, dispatcher, name):
                assert None == dispatcher.log (
                        '%r unresolved' % name, 'debug'
                        )
                dispatcher.handle_close ()

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
                
        def client_meter (self, dispatcher):
                assert None == dispatcher.log (
                        'in="%d" out="%d"' % (
                                dispatcher.ac_in_meter, 
                                dispatcher.ac_out_meter
                                ),  'debug'
                        )
                self.ac_in_meter += dispatcher.ac_in_meter
                self.ac_out_meter += dispatcher.ac_out_meter
                self.client_dispatched += 1

        def client_close (self, dispatcher):
                "remove the dispatcher from cache and increment dispatched"
                self.client_meter (dispatcher)
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
                self.client_dispatched = \
                        self.ac_in_meter = self.ac_out_meter = 0

        def client_shutdown (self):
                "close all client dispatchers when done"
                for dispatcher in self.client_dispatchers ():
                        dispatcher.close_when_done ()
                        

class Cache (Manager):

        def __init__ (
                self, timeout=3, precision=1, family=socket.AF_INET
                ):
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
                self, Dispatcher, name, 
                pool=2, timeout=3, precision=1, family=socket.AF_INET
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
                if size >= self.client_pool:
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
                self.client_meter (dispatcher)
                self.client_managed.remove (dispatcher)
                dispatcher.client_manager = None


def resolved (manager):
        "allways resolved for unresolved dispatcher address"
        manager.client_resolved = (lambda name: True)
        manager.client_resolve = None


def unmeter (dispatcher):
        "remove stream decorators from a client dispatcher"
        del (
                dispatcher.recv, 
                dispatcher.send, 
                dispatcher.handle_close
                )

def meter (dispatcher, when):
        "decorate a client dispatcher with stream meters"
        async_limits.meter_recv (dispatcher, when)
        async_limits.meter_send (dispatcher, when)
        def handle_close ():
                unmeter (dispatcher)
                dispatcher.handle_close ()
                dispatcher.client_manager.client_close (dispatcher)
                
        dispatcher.handle_close = handle_close

def inactive (manager, timeout):
        "meter I/O and limit inactivity for client streams"
        def decorate (dispatcher, when):
                meter (dispatcher, when)
                dispatcher.limit_inactive = manager.client_inactive
                
        manager.client_decorate = decorate
        manager.client_inactive = timeout
        manager.client_limit = async_limits.inactive


def limited (manager, timeout, inBps, outBps):
        "throttle I/O and limit inactivity for client streams"
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
                        dispatcher, when, manager.ac_in_throttle_Bps
                        )
                async_limits.throttle_writable (
                        dispatcher, when, manager.ac_out_throttle_Bps
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
                        dispatcher.client_manager.client_close (dispatcher)
                        
                dispatcher.handle_close = handle_close

        manager.client_decorate = throttle
        manager.ac_in_throttle_Bps = inBps
        manager.ac_out_throttle_Bps = outBps
        manager.client_limit = async_limits.limit


def rationed (manager, timeout, inBps, outBps):
        manager.ac_in_ration_Bps = inBps
        manager.ac_out_ration_Bps = outBps
        def throttle_in ():
                return int (manager.ac_in_ration_Bps / max (len (
                        manager.client_managed
                        ), 1))

        def throttle_out ():
                return int (manager.ac_out_ration_Bps / max (len (
                        manager.client_managed
                        ), 1))

        limited (manager, timeout, throttle_in, throttle_out)


class Pipeline (object):
        
        "a pipeline mix-in for dispatcher"

        pipeline_sleeping = False
        pipeline_keep_alive = False

        def pipeline_set (self, requests=None, responses=None):
                self.pipeline_requests = requests or collections.deque ()
                self.pipeline_responses = responses or collections.deque ()

        def pipeline (self, request):
                self.pipeline_requests.append (request)
                if self.pipeline_sleeping:
                        self.pipeline_sleeping = False
                        self.pipeline_wake_up ()

        def pipeline_wake_up (self):
                assert None == self.log (
                        'pipeline_wake_up', 'unimplemented'
                        )