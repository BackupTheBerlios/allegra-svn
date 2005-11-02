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

import sys, socket, time, asynchat

from allegra import loginfo, async_loop


class TCP_client_channel (loginfo.Loginfo, asynchat.async_chat):

	tcp_connect_timeout = 10 # a ten seconds timeout for connection

	def __init__ (self, terminator=None):
		asynchat.async_chat.__init__ (self)
		if terminator:
			self.set_terminator (terminator)

	def __repr__ (self):
		return '<tcp-client-channel id="%x"/>' % id (self)

	# take precedence over the asyncore dispatcher logging facility
	#
	log = log_info = loginfo.Loginfo.loginfo_log

	def close (self):
		assert None == self.log ('close', 'debug')
		self.del_channel ()
		self.socket.close ()
		self.connected = 0
		self.closing = 1

        def handle_error (self):
		assert None == self.log ('handle_error', 'debug')
                t, v = sys.exc_info ()[:2]
                if t is SystemExit:
                        raise t, v # don't catch SystemExit!
                
                self.loginfo_traceback ()
		self.close ()

	#def handle_expt (self):
	#	assert None == self.log ('<handle-expt/>', '')
        #       self.close ()

        def handle_close (self):
		assert None == self.log ('handle_close', 'debug')
		self.close ()
			
	def handle_connect (self):
		assert None == self.log ('handle_connected', 'debug')

	def collect_incoming_data (self, data):
		assert None == self.log (data, 'debug')
			
	def found_terminator (self):
		assert None == self.log ('found_terminator', 'debug')
		
        def tcp_connect (self, addr):
		if self.connected:
			return True

                self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
                try:
			self.connect (addr)
		except:
			self.loginfo_traceback ()
			return False
			
		assert None == self.log ('connect %s %d' % addr, 'debug')
		async_loop.async_schedule (
			time.time () + self.tcp_connect_timeout,
			self.tcp_timeout
			)
		return True

	def tcp_timeout (self, when):
		if not (self.connected or self.closing):
			assert None == self.log (
				'connect_timeout'
				' %d' % self.tcp_connect_timeout, 'debug'
				)
			self.close ()
			

from allegra.async_limits import Async_limit_in, Async_limit_out

class TCP_client_limit (TCP_client_channel, Async_limit_in, Async_limit_out):

	tcp_inactive_timeout = 60	# one minute timeout for inactive client
	tcp_defer_precision = 10	# ten seconds precision for defered

	def __init__ (self, addr):
		TCP_client_channel.__init__ (self, addr)
		Async_limit_in.__init__ (self)
		Async_limit_out.__init__ (self)
		self.async_limit_send ()
		self.async_limit_recv ()

	def __repr__ (self):
		return '<tcp-client-limit id="%x"/>' % id (self)

	def tcp_timeout (self, when):
		if self.connected:
			return (
				when + self.tcp_defer_precision,
				self.tcp_client_defer
				)
				
		if not self.closing:
			assert None == self.log (
				'connect_timeout'
				' %d' % self.tcp_connect_timeout, 'debug'
				)
			self.handle_close ()

	def tcp_client_defer (self, when):
		if not self.closing and self.connected and (
			when - max (self.async_when_in, self.async_when_out)
			) > self.tcp_inactive_timeout:
			assert None == self.log ('inactive', 'debug')
			self.close ()

		return when + self.tcp_defer_precision, self.tcp_client_defer


from allegra.async_limits import Async_throttle_in, Async_throttle_out

class TCP_client_throttle (
	TCP_client_limit, Async_throttle_in, Async_throttle_out
	):

	tcp_inactive_timeout = 10	# ten seconds timeout for inactive client
	tcp_defer_precision = 1		# one second precision for defered

	def __init__ (self, addr):
		TCP_client_limit.__init__ (self, addr)
		self.async_limit_read ()
		self.async_limit_write ()

	def tcp_client_defer (self, when):
		self.async_throttle_in (when)
		self.async_throttle_out (when)
		return TCP_client_limit.tcp_client_defer (self, when)
