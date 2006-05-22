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

"Three kind of TCP servers for a wide range of practical applications"

import sys, socket, time

from allegra import (
        async_loop, async_core, async_limits, async_net, async_chat
        )


class TCP_server_echo_net (async_net.Async_net):
        
        def async_net_continue (self, data):
                self.log (data)
                self.ac_out_buffer += '%d:%s,' % (len (data), data)
                

class TCP_server_echo_line (async_chat.Async_chat):
        
        echo_line = ''

        def collect_incoming_data (self, data):
                self.echo_line += data
                
        def found_terminator (self):
                self.log (self.echo_line)
                self.push (self.echo_line+'\n')
                self.echo_line = ''
                

class TCP_server (async_core.Async_dispatcher):
        
        # A simple TCP server, usefull for any peer with unrestricted 
        # bandwith use and many single clients. practically, that's the
        # case for peers at both the user-interface and the back-end of a
        # network application. As simple as it is, it fits the requirements
        # to develop TCP applications for large grids where bandwith is
        # is redundant or better managed independantly.

        TCP_SERVER_LISTEN = 1024 # lower this to 5 if your OS complains
	TCP_SERVER_CHANNEL = TCP_server_echo_line
	
        tcp_server_clients_limit = 1 # a strict limit on connections per IP

        def __init__ (self, addr):
                self.tcp_server_clients = {}
                self.tcp_server_channels = []
                async_core.Async_dispatcher.__init__ (self)
                self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
                self.set_reuse_addr ()
                self.bind (addr)
                self.listen (self.TCP_SERVER_LISTEN)
                self.log ('start ip="%s" port="%d"' % self.addr, 'info')

	def __repr__ (self):
		return 'tcp-server id="%x"' % id (self)

        def readable (self):
                return self.accepting

        def writable (self):
                return 0

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

                if self.tcp_server_clients.setdefault (
                        addr[0], 0
                        ) < self.tcp_server_clients_limit:
                        self.tcp_server_clients[addr[0]] += 1
                else:
                        conn.close ()
                        assert None == self.log (
                                'connection-limit ip="%s"' % addr[0],
                                'error'
                                )
                        return

                channel = self.TCP_SERVER_CHANNEL (conn)
                channel.addr = addr
                def handle_close ():
                        self.tcp_server_handle_close (channel)
                channel.handle_close = handle_close
                self.tcp_server_channels.append (channel)
                self.tcp_server_accept (channel)
                return channel
                
        def handle_close (self):
                "stop the server now, close all channels now, then finalize"
                if len (self.tcp_server_channels) > 0:
                        for channel in tuple (self.tcp_server_channels):
                                channel.handle_close ()
                self.close ()
                self.tcp_server_stop ()
                        
	def tcp_server_accept (self, channel):
                assert None == self.log ('%r' % channel, 'accepted')
                
        def tcp_server_handle_close (self, channel):
                "remove a closed channel from the managed list, update limits"
                self.tcp_server_channels.remove (channel)
                if self.tcp_server_clients[channel.addr[0]] > 1:
                        self.tcp_server_clients[channel.addr[0]] -= 1
                else:
                        del self.tcp_server_clients[channel.addr[0]]
                channel.close ()
                del channel.handle_close # break circular reference!
                self.tcp_server_close (channel)

        def tcp_server_close (self, channel):
                assert None == self.log ('%r' % channel, 'closed')
                
        def tcp_server_stop (self):
                "called once the server stopped, assert debug log and close"
                assert None == self.log ('stop', 'debug')
                
        def tcp_server_catch (self):
                async_loop.async_catch = self.async_catch
                self.async_catch = None
                self.handle_close ()
                return True
        
        def tcp_server_throw (self):
                async_loop.async_catch = self.async_catch
                self.async_catch = None
                self.handle_close ()
                return async_loop.async_catch ()
        

class TCP_server_limit (TCP_server):
        
        # A practical server that meter I/O and close inactive sessions
        # after a specified period. This is a usefull implementation for 
        # pipelined or statefull API, when TCP sessions are kept-alive
        # but also may "stall" (like some HTTP/1.1 client do).
        
        tcp_server_timeout = 3
        tcp_server_precision = 1
        tcp_server_shutdown = False

        def handle_close (self):
                assert None == self.log ('handle-close', 'debug')
                self.tcp_server_shutdown = True
                if len (self.tcp_server_channels) > 0:
                        for channel in tuple (self.tcp_server_channels):
                                channel.close_when_done ()
                        return
                                
                self.close ()
                self.tcp_server_stop ()

        def handle_accept (self):
                channel = TCP_server.handle_accept (self)
                if channel == None:
                        return
                        
                channel.tcp_server_when = now = time.time ()
                async_limits.meter_recv (channel, now)
                async_limits.meter_send (channel, now)
                if (
                        self.tcp_server_precision >0 and
                        len (self.tcp_server_channels) == 1
                        ):
                        async_loop.async_schedule (
                                time.time () + self.tcp_server_precision,
                                self.tcp_server_defer
                                )
                        assert None == self.log ('defered-start', 'debug')
                return channel

        def tcp_server_defer (self, when):
                if self.tcp_server_channels:
                        for channel in self.tcp_server_channels:
                                self.tcp_server_inactive (channel, when)
                        return (
                                when + self.tcp_server_precision,
                                self.tcp_server_defer
                                ) # continue to defer
                
                assert None == self.log ('defer-stop', 'debug')
                if self.tcp_server_shutdown:
                        self.close ()
                        self.tcp_server_stop ()
                return
                
        def tcp_server_inactive (self, channel, when):
                if not channel.closing and channel.connected and (
                        when - max (
                                channel.ac_in_when, channel.ac_out_when
                                )
                        ) > self.tcp_server_timeout:
                        channel.log ('inactive', 'info')
                        channel.handle_close ()
                        
        def tcp_server_handle_close (self, channel):
                channel.log ('bytes in="%d" out="%d" seconds="%f"' % (
                        channel.ac_in_meter, 
                        channel.ac_out_meter,
                        (time.time () - channel.tcp_server_when)
                        ), 'info')
                TCP_server.tcp_server_handle_close (self, channel)
                del channel.recv, channel.send # remove the async_limits


class TCP_server_throttle (TCP_server_limit):
        
        # A TCP server that throttles I/O to a global rate, effectively
        # rationating a total future bandwith to each of its peers. This
        # is a usefull implementation for any peer with limited bandwith
        # (those on the network edge), but also network API peer for which
        # I/O should be available, audited ... and accounted for.
        #
        # Wether you need to build a bandwith-savy application for an edge 
        # appliance or develop an API service made with strict management
        # and audit of I/O, this is 99% of what you want out-of-the-box
        # from a TCP server base class.
        
        async_throttle_in_Bps = 4096 # ac_in_buffer_size?
        async_throttle_out_Bps = 4096 # ac_in_buffer_size?

	def handle_accept (self):
		channel = TCP_server_limit.handle_accept (self)
                if channel == None:
                        return

                when = time.time ()
                self.tcp_server_throttle ()
                async_limits.throttle_readable (
                        channel, when, self.tcp_server_throttle_in
                        )
                async_limits.throttle_writable (
                        channel, when, self.tcp_server_throttle_out
                        )
		return channel

        def tcp_server_throttle (self):
                clients = len (self.tcp_server_clients)
                if clients == 0:
                        return
                
                self.tcp_server_throttle_in_Bps = int (
                        self.async_throttle_in_Bps / clients
                        )
                self.tcp_server_throttle_out_Bps = int (
                        self.async_throttle_out_Bps / clients
                        )

        def tcp_server_defer (self, when):
                for channel in self.tcp_server_channels:
                        async_limits.throttle_in (channel, when)
                        async_limits.throttle_out (channel, when)
                return TCP_server_limit.tcp_server_defer (self, when)
        
	def tcp_server_throttle_in (self):
                return self.tcp_server_throttle_in_Bps

	def tcp_server_throttle_out (self):
                return self.tcp_server_throttle_out_Bps

	def tcp_server_handle_close (self, channel):
                # remove circular references (a perfect example of why private
                # APIs *are* a wrong coding practice!)
                #
		TCP_server_limit.tcp_server_handle_close (self, channel)
                async_limits.unthrottle_readable (channel)
                async_limits.unthrottle_writable (channel)
                self.tcp_server_throttle ()
                
                
# Note about this implementation
#
# This module provides three kind of TCP servers: with a limits for the
# number of sessions by client IP address; with a limit on inactive
# session, using timers and counters attached to each session; with a limit
# on total bandwith and rationing equally per session.
#
# Those three kind of TCP servers can manage any async_code dispatcher,
# async_net or async_chat channels. And the same TCP server channel or 
# dispatcher may be managed by all three kinds of servers indifferently.
# Which means that there is only one channel class to implement in order
# to write a peer, a server and a throttler for a given protocol and its 
# application(s).
#
# This module provides the one obvious right way for an application to
# limit a peer depending on the network of the IP address it is listening
# to: no limits for 127.0.0.0; counters, timers and inactive limit for 
# 192.168.0.0 and 10.0.0.0; throttled for all public Internet addresses.
#
# The rational beeing: that you can afford no limits on a loopback device;
# that you don't have to limit bandwith on a LAN but should save CPU and
# memory from zombie clients and audit your network down to the byte; 
# that you should rationate public access to your private network.
#
# Application developpers may not use that rule, use the server of that
# suites best their purposes and change the default limits to fit each
# protocol and application. This module provides the constants and logic
# that suites a multiprotocol peer on the edge of a the network: one
# client session per IP address, limited to a 3 seconds inactive timeout
# and a 4KBps I/O limit on a public network.

#
# TODO: factor out the server_* API out of tcp_server_* interfaces.
#       then move it to its own server.py module.
#