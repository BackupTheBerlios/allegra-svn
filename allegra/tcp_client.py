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

"""DESCRIPTION

One base class to derive TCP client implementation and a few functions 
that add practical limits to guard a peer against zombie sessions (inactive 
longer than the limit) and effectively rationate I/O bandwith.

SYNOPSYS

...

"""

import sys, socket, time

from allegra import loginfo, async_loop, async_chat, async_limits


class TCP_client_channel (async_chat.Async_chat):

	tcp_connect_timeout = 10 # a ten seconds timeout for connection
	tcp_client_defer = None
	
	def __repr__ (self):
		return 'tcp-client-channel id="%x"' % id (self)

	def collect_incoming_data (self, data):
		assert None == self.log (data, 'debug')
			
	def found_terminator (self):
		assert None == self.log ('found-terminator', 'debug')
		
        def tcp_connect (self, addr):
        	"create a socket and try to connect to addr, return success"
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
		"if connected, continue to defer, otherwise handle close"
		if self.connected:
			if self.tcp_client_defer != None:
				return (
					when + self.tcp_client_precision,
					self.tcp_client_defer
					)
			return
				
		if not self.closing:
			assert None == self.log (
				'connect-timeout'
				' %d' % self.tcp_connect_timeout, 'debug'
				)
			self.handle_close ()
			

class TCP_client_echo (TCP_client_channel):
	
	"The simplest derived class, a netline logger."

	def __init__ (self):
		async_chat.Async_chat.__init__ (self)
                self.set_terminator ('\n')
                self.echo_buffer = ''
                
        def collect_incoming_data (self, data):
                self.echo_buffer += data
                
        def found_terminator (self):
                self.log (self.echo_buffer)
                self.echo_buffer = ''
                

def tcp_client_inactive (channel, when):
	if not channel.closing and channel.connected and (
		when - max (channel.async_when_in, channel.async_when_out)
		) > channel.tcp_client_inactive:
		assert None == channel.log ('inactive', 'debug')
		channel.handle_close ()
		return

	return when + channel.tcp_client_precision, channel.tcp_client_defer

def tcp_client_limit (channel, inactive=60, precision=10):
	async_limits.async_limit_in (channel)
	async_limits.async_limit_out (channel)
	channel.tcp_client_inactive = inactive
	channel.tcp_client_precision = precision
	channel.tcp_client_defer = tcp_client_inactive
	return channel
	

def tcp_client_throttle_defer (channel, when):
	async_throttle_in_defer (channel, when)
	async_throttle_out_defer (channel, when)
	return tcp_client_inactive (channel, when)

def tcp_client_throttle (
	channel, 
	throttle_in=async_limits.FourKBps, 
	throttle_out=async_limits.FourKBps, 
	inactive=60, precision=10
	):
	TCP_client_limit (channel, inactive, precision)
	channel.tcp_client_defer = tcp_client_throttle
	return channel


def tcp_client_throttle_out_defer (channel, when):
	async_throttle_out_defer (channel, when)
	return tcp_client_inactive (channel, when)

def tcp_client_throttle_out (
	channel, Bps=async_limits.FourKBps, inactive=60, precision=10
	):
	tcp_client_limit (channel, inactive, precision)
	channel.async_throttle_out_Bps = Bps
	channel.tcp_client_defer = tcp_client_throttle_out_defer
	return channel


def tcp_client_throttle_in_defer (channel, when):
	async_throttle_in_defer (channel, when)
	return tcp_client_inactive (channel, when)

def tcp_client_throttle_in (
	channel, Bps=async_limits.FourKBps, inactive=60, precision=10
	):
	tcp_client_limit (channel, inactive, precision)
	channel.async_throttle_in_Bps = Bps
	channel.tcp_client_defer = tcp_client_throttle_in_defer
	return channel
	
