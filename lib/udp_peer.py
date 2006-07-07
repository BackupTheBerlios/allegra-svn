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

import sys, socket, random #, asyncore, errno 

from allegra import async_core


class UDP_dispatcher (async_core.Dispatcher):

	def __init__ (self, ip, port=None):
                # binds a channel to a given ip address, pick a random port
                # above 8192 if none provided, and handle error.
                #
		self.create_socket (socket.AF_INET, socket.SOCK_DGRAM)
		addr = ip, port or (
			(abs (hash (random.random ())) >> 16) + 8192
			)
		try:
			self.bind (addr)
		except socket.error:
			self.handle_error ()
		else:
			self.connected = True # ? somehow connected ...
                        assert None == self.log (
                                'bind ip="%s" port="%d"' % self.addr, 'debug'
                                )

	def __repr__ (self):
		return 'udp-dispatcher id="%x"' % id (self)

	def readable (self):
		return self.connected # UDP peer may be "disconnected"

	def writable (self):
		return 0 # UDP protocols are *never* writable as for asyncore

	# ECONNRESET, ENOTCONN, ESHUTDOWN
	#
        # catch all socket exceptions for reading and writing, this is UDP
        # and the protocol implementation derived from this dispatcher
        # should handle error without closing the channel.
	#
	# basically, I know little about how UDP sockets behave (less how 
	# they do on various systems ;-)

        def sendto (self, data, peer):
		try:
			return self.socket.sendto (data, peer)
		
		except socket.error:
			self.handle_error ()
			return 0

	def recvfrom (self, datagram_size):
		try:
			return self.socket.recvfrom (datagram_size)

		except socket.error:
			self.handle_error ()
			return '', None

	def handle_read (self):
		# to subclass
		data, peer = self.recvfrom ()
		if peer != None:
			assert None == self.log (
				'recvfrom ip="%s" port"%d" bytes="%d"' % (
					peer[0], peer[1], len (data)
					), 'debug'
				)
		else:
			assert None == self.log ('recvfrom', 'debug')


# TODO: add a UDP pipeline implementation that behaves like asynchat?