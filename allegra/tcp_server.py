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

from allegra import async_loop, async_core, async_chat, async_limits


class TCP_server_echo_line (async_chat.Async_chat):

        def __init__ (self, conn, addr):
                assert None == self.log (
                        'accepted ip="%s" port="%d"' % addr, 'debug'
                        )
                self.addr = addr               
                async_chat.Async_chat.__init__ (self, conn)
                self.set_terminator ('\n')
                self.tcp_server_buffer = ''
                
        def collect_incoming_data (self, data):
                self.tcp_server_buffer += data
                
        def found_terminator (self):
                self.log (self.tcp_server_buffer)
                self.push (self.tcp_server_buffer+'\n')
                self.tcp_server_buffer = ''
                

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

		self.tcp_server_accept (conn, addr)
                
        def handle_close (self):
                "stop the server now, close all channels now, then finalize"
                if len (self.tcp_server_channels) > 0:
                        for channel in tuple (self.tcp_server_channels):
                                channel.handle_close ()
                self.close ()
                self.tcp_server_stopped ()
                        
	def tcp_server_accept (self, conn, addr):
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

                channel = self.TCP_SERVER_CHANNEL (conn, addr)
                def tcp_server_close ():
                        self.tcp_server_close (channel)
                channel.handle_close = tcp_server_close
                self.tcp_server_channels.append (channel)
		return channel

        def tcp_server_close (self, channel):
                "remove a closed channel from the managed list, update limits"
                self.tcp_server_channels.remove (channel)
                if self.tcp_server_clients[channel.addr[0]] > 1:
                        self.tcp_server_clients[channel.addr[0]] -= 1
                else:
                        del self.tcp_server_clients[channel.addr[0]]
                channel.close ()
                del channel.handle_close # break circular reference!

        def tcp_server_stopped (self):
                "called once the server stopped, assert debug log and close"
                assert None == self.log ('stopped', 'debug')
                        

class TCP_server_limit (TCP_server):
        
        # A practical server that meter I/O and close inactive sessions
        # after a specified period. This is a usefull implementation for 
        # pipelined or statefull API, when TCP sessions are kept-alive
        # but also may "stall" (like some HTTP/1.1 client do).
        
        tcp_server_inactive = 60
        tcp_server_precision = 10

        def handle_close (self):
                assert None == self.log ('stop', 'debug')
                if len (self.tcp_server_channels) > 0:
                        self.closing = 1
                        for channel in tuple (self.tcp_server_channels):
                                channel.close_when_done ()
                        return
                                
                self.close ()
                self.tcp_server_stopped ()

        def tcp_server_accept (self, conn, addr):
                channel = TCP_server.tcp_server_accept (self, conn, addr)
                if channel == None:
                        return
                        
                channel.tcp_server_when = now = time.time ()
                async_limits.async_limit_in (channel, now)
                async_limits.async_limit_out (channel, now)
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
                assert None == self.log ('defer', 'debug')
                for channel in self.tcp_server_channels:
                        self.tcp_server_inactive (channel, when)
                if self.tcp_server_channels:
                        return (
                                when + self.tcp_server_precision,
                                self.tcp_server_defer
                                ) # continue to defer
                
                assert None == self.log ('defer-stop', 'debug')
                if self.closing:
                        self.close ()
                        self.tcp_server_stopped ()
                return None
                
        def tcp_server_inactive (self, channel, when):
                if not channel.closing and channel.connected and (
                        when - max (
                                channel.async_when_in, channel.async_when_out
                                )
                        ) > self.tcp_inactive_timeout:
                        channel.log ('inactive', 'info')
                        channel.handle_close ()
                        
        def tcp_server_close (self, channel):
                channel.log ('bytes in="%d" out="%d" seconds="%f"' % (
                        channel.async_bytes_in, 
                        channel.async_bytes_out,
                        (time.time () - channel.tcp_server_when)
                        ), 'info')
                TCP_server.tcp_server_close (self, channel)


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
        
        tcp_server_throttle_in_Bps = 4096 # ac_in_buffer_size
        tcp_server_throttle_out_Bps = 4096 # ac_in_buffer_size

	def tcp_server_accept (self, conn, addr):
		channel = TCP_server_limit.tcp_server_accept (
                        self, conn, addr
                        )
                if channel == None:
                        return

                async_limits.async_throttle_in (
                        channel, self.tcp_server_throttle_in
                        )
                async_limits.async_throttle_out (
                        channel, self.tcp_server_throttle_out
                        )
		return channel

        def tcp_server_defer (self, when):
                for channel in self.tcp_server_channels:
                        async_limits.async_throttle_in_defer (channel, when)
                        async_limits.async_throttle_out_defer (channel, when)
                return TCP_server_limit.tcp_server_defer (self, when)
        
	def tcp_server_throttle_in (self):
		return int (
                        self.async_throttle_in_Bps / 
                        len (self.tcp_server_clients)
                        )

	def tcp_server_throttle_out (self):
		return int (
                        self.async_throttle_out_Bps / 
                        len (self.tcp_server_clients)
                        )

	def tcp_server_close (self, channel):
                # remove circular references (a perfect example of why private
                # APIs *are* a wrong coding practice!)
                #
		del channel.async_throttle_in_Bps
                del channel.async_throttle_out_Bps
		TCP_server_limit.tcp_server_close (self, channel)
