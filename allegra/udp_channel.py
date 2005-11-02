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

import sys, socket, random, asyncore #, errno 

from allegra import loginfo


class UDP_dispatcher (asyncore.dispatcher, loginfo.Loginfo):

	udp_datagram_size = 512

	def __init__ (self, ip, port=None):
		asyncore.dispatcher.__init__ (self)
		self.create_socket (socket.AF_INET, socket.SOCK_DGRAM)
		# binds a channel to a given ip address, pick a random port
		# above 8192 if none provided, and handle error.
		self.addr = ip, port or (
			(abs (hash (random.random ())) >> 16) + 8192
			)
		assert None == self.log (
			'<bind ip="%s" port="%d"/>' % self.addr, 'debug'
			)
		try:
			self.bind (self.addr)
		except socket.error:
			self.handle_error ()
		else:
			self.connected = 1

	def __repr__ (self):
		return '<udp-dispatcher id="%x"/>' % id (self)

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

	def close (self):
		assert None == self.log ('<close/>', 'debug')
		self.del_channel ()
		self.socket.close ()
		self.connected = 0
		self.closing = 1

	def handle_read (self):
		# to subclass
		data, peer = self.recvfrom ()
		if peer != None:
			assert None == self.log (
				'<recvfrom ip="%s" port"%d"/>'
				'<![CDATA[%s]]!>' % (
					peer[0], peer[1], data
					), 'debug'
				)
		else:
			assert None == self.log ('<recvfrom/>', 'debug')

        def handle_error (self):
        	# to subclass
                t, v = sys.exc_info ()[:2]
                if t is SystemExit:
                        raise t, v

		self.loginfo_traceback ()

	def handle_close (self):
		# to subclass
		self.close ()

	log = log_info = loginfo.Loginfo.loginfo_log

# TODO: add a UDP pipeline implementation that behaves like asynchat?