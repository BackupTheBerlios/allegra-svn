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

import sys
import socket
from time import time

from asynchat import async_chat as Async_chat
from asyncore import dispatcher as Dispatcher

from allegra.loginfo import Loginfo
from allegra import async_loop

class TCP_server_channel (Async_chat, Loginfo):

        def __init__ (self, conn, addr):
                self.addr = addr               
                Async_chat.__init__ (self, conn)
                assert None == self.log (
                        '<connected ip="%s" port="%d"/>' % self.addr
                        )

        def __repr__ (self):
                return '<tcp-server-channel id="%x"/>' % id (self)

	log = log_info = Loginfo.loginfo_log

        def recv (self, buffer_size):
                try:
			data = Async_chat.recv (self, buffer_size)
                except MemoryError:
                        sys.exit ("Out of Memory!") # do not even try to log!

                return data

	def handle_expt (self):
                self.loginfo_traceback ()

        def handle_error (self):
                t, v = sys.exc_info ()[:2]
                if t is SystemExit:
                        raise t, v

		self.loginfo_traceback ()
		self.close ()

	def close (self):
                assert None == self.log ('<close/>', '')
		self.del_channel ()
		self.socket.close ()
		self.closing = 1
                self.connected = 0
                self.tcp_server_close (self)
                
	def tcp_server_defer (self, when):
		assert None == self.log ('<defer/>', '')


class TCP_server (Dispatcher, Loginfo):
        
        # a simple limited TCP server with an interface for defered
        # inspection of channel state and scavenging. usefull for any
        # peer with limited bandwith.

        TCP_SERVER_LISTEN = 1024		# lower this to 5 if your OS complains
	TCP_SERVER_CHANNEL = TCP_server_channel # a TCP server channel factory
	
        tcp_server_clients_limit = 1 	# a strict limit on the number of connections per IP
	tcp_server_precision = 10	# a precision of 10 second for the defered events

        def __init__ (self, addr):
                self.tcp_server_clients = {}
                self.tcp_server_channels = []
                Dispatcher.__init__ (self)
                self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
                self.set_reuse_addr ()
                self.bind (addr)
                self.listen (self.TCP_SERVER_LISTEN)
                assert None == self.log (
                        '<start ip="%s" port="%d"/>' % self.addr, ''
                        )

	def __repr__ (self):
		return '<tcp-server id="%x"/>' % id (self)

        def readable (self):
                return self.accepting

        def writable (self):
                return 0

        def close (self):
                assert None == self.log ('<close/>', '')
                self.del_channel ()
                self.socket.close ()
                self.closing = 1
                self.connected = 0

        def handle_read (self):
                assert None == self.log ('<handle-read/>', '')

        def handle_connect (self):
                assert None == self.log ('<handle-connect/>', '')

        def handle_accept (self):
                try:
                        conn, addr = self.accept ()
                except socket.error:
                        # linux: on rare occasions we get a bogus socket back from
                        # accept.  socketmodule.c:makesockaddr complains that the
                        # address family is unknown.  We don't want the whole server
                        # to shut down because of this.
                        assert None == self.log (
                                '<accept-bogus-socket/>', '<error/>'
                                )
                        return
                
                except TypeError:
                        # unpack non-sequence.  this can happen when a read event
                        # fires on a listening socket, but when we call accept()
                        # we get EWOULDBLOCK, so dispatcher.accept() returns None.
                        # Seen on FreeBSD3.
                        assert None == self.log (
                                '<accept-would-block/>', '<error/>'
                                )
                        return

		self.tcp_server_accept (conn, addr)
                
        def handle_error (self):
                t, v = sys.exc_info ()[:2]
                if t is SystemExit:
                        raise t, v

		self.loginfo_traceback ()
		self.close ()

        def handle_close (self):
                assert None == self.log ('<handle-close/>', '')

        log = log_info = Loginfo.loginfo_log

	def tcp_server_accept (self, conn, addr):
		if self.tcp_server_clients.setdefault (
			addr[0], 0
			) < self.tcp_server_clients_limit:
			self.tcp_server_clients[addr[0]] += 1
		else:
			conn.close ()
                        assert None == self.log (
                                '<connection-limit ip="%s"/>' % addr[0], ''
                                )
			return

		channel = self.TCP_SERVER_CHANNEL (conn, addr)
                channel.tcp_server_close = self.tcp_server_close
		self.tcp_server_channels.append (channel)
                if (
                        self.tcp_server_precision >0 and
                        len (self.tcp_server_channels) == 1
                        ):
                        async_loop.async_defer (
                                time () + self.tcp_server_precision,
                                self.tcp_server_defer
                                )
                        assert None == self.log ('<defered-start/>', '')
		return channel

        def tcp_server_close (self, channel):
                self.tcp_server_channels.remove (channel)
                if self.tcp_server_clients[channel.addr[0]] > 1:
                        self.tcp_server_clients[channel.addr[0]] -= 1
                else:
                        del self.tcp_server_clients[channel.addr[0]]
                del channel.tcp_server_close

        def tcp_server_stop (self):
                assert None == self.log ('<stop/>', '')
                if len (self.tcp_server_channels) > 0:
                        self.accepting = 0
                        for channel in tuple (self.tcp_server_channels):
                                channel.close ()
                        if self.tcp_server_precision > 0:
                                self.tcp_server_defer_stop = \
                                        self.tcp_server_finalize
                                return
                                
                self.tcp_server_finalize ()
                        
        def tcp_server_finalize (self):
                assert None == self.log ('<finalize/>')
                        
        def tcp_server_defer (self, when):
                for channel in self.tcp_server_channels:
                        channel.tcp_server_defer (when)
                if self.tcp_server_channels:
                        return (
                                when + self.tcp_server_precision,
                                self.tcp_server_defer
                                ) # continue to defer
                                
                self.tcp_server_defer_stop ()
                return None
                
        def tcp_server_defer_stop (self):
                assert None == self.log ('<defered-stop/>', '')


from allegra.async_limits import Async_limit_in, Async_limit_out

class TCP_server_limit (TCP_server_channel, Async_limit_in, Async_limit_out):

	tcp_inactive_timeout = 60 # one minute timeout for inactive client

	def __init__ (self, conn, addr):
		TCP_server_channel.__init__ (self, conn, addr)
		self.async_limit_send ()
		self.async_limit_recv ()
		
	def tcp_server_defer (self, when):
		if not self.closing and self.connected and (
			when - max (self.async_when_in, self.async_when_out)
			) > self.tcp_inactive_timeout:
			assert None == self.log ('<inactive/>', '')
			self.handle_close ()
			

from allegra.async_limits import Async_throttle_in, Async_throttle_out

class TCP_server_throttle (TCP_server_limit, Async_throttle_in, Async_throttle_out):

	tcp_inactive_timeout = 60	# one minute timeout for inactive client

	def __init__ (self, conn, addr):
		TCP_server_limit.__init__ (self, conn, addr)
		self.async_limit_read ()
		self.async_limit_write ()

	def tcp_server_defer (self, when):
		self.async_throttle_in (when)
		self.async_throttle_out (when)
		return TCP_server_limit.tcp_server_defer (self, when)

	
class TCP_throttler (TCP_server):

	TCP_SERVER_CHANNEL = TCP_server_throttle

	async_throttle_in_Bps = async_throttle_out_Bps = 8192 # 8KBps, 64Kbps

	def tcp_server_accept (self, conn, addr):
		channel = TCP_server.tcp_server_accept (self, conn, addr)
		if channel:
			channel.async_throttle_in_Bps = self.tcp_throttle_in
			channel.async_throttle_out_Bps = self.tcp_throttle_out
		return channel

	def tcp_throttle_in (self):
		return int (self.async_throttle_in_Bps / len (self.tcp_server_clients))

	def tcp_throttle_out (self):
		return int (self.async_throttle_out_Bps / len (self.tcp_server_clients))

	def tcp_server_close (self, channel):
		del channel.async_throttle_in_Bps, channel.async_throttle_out_Bps
		TCP_server.tcp_server_close (self, channel)
