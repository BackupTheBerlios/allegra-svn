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

from allegra import async_core, finalization


class UDP_dispatcher (
	async_core.Async_dispatcher, finalization.Finalization
	):

	udp_datagram_size = 512

	def __init__ (self, ip, port=None):
		async_core.Async_dispatcher.__init__ (self)
		self.create_socket (socket.AF_INET, socket.SOCK_DGRAM)
		# binds a channel to a given ip address, pick a random port
		# above 8192 if none provided, and handle error.
		self.addr = ip, port or (
			(abs (hash (random.random ())) >> 16) + 8192
			)
		assert None == self.log (
			'bind ip="%s" port="%d"' % self.addr, 'debug'
			)
		try:
			self.bind (self.addr)
		except socket.error:
			self.handle_error ()
		else:
			self.connected = 1

	def __repr__ (self):
		return 'udp-dispatcher id="%x"' % id (self)

        def finalization (self, finalized):
                assert None == self.log ('finalized', 'debug')

	def readable (self):
		return self.connected # UDP peer may be "disconnected"

	def writable (self):
		return 0 # UDP protocols are *allways* writable

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

	def recvfrom (self):
		try:
			return self.socket.recvfrom (self.udp_datagram_size)

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