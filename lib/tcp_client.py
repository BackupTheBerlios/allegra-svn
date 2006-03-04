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

import sys, socket, time, collections

from allegra import (
	loginfo, async_loop, async_limits, async_net, async_chat
        )


class TCP_client_channel (object):

	tcp_client_defer = None
	
        def tcp_connect (self, addr, timeout=3):
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
			time.time () + timeout, self.tcp_timeout
			)
		return True

	def tcp_timeout (self, when):
		"if connected, continue to defer, otherwise handle close"
		if not self.connected and not self.closing:
			assert None == self.log (
				'connect-timeout', 'debug'
				)
			self.handle_close ()


class TCP_client_net (async_net.Async_net, TCP_client_channel):
	
	"The simplest netstring client, a netline logger."


class TCP_client_line (async_chat.Async_chat, TCP_client_channel):
	
	"The simplest asynchat client, a netline logger."

        echo_line = ''
                
	def __repr__ (self):
		return 'line-client-channel id="%x"' % id (self)

        def collect_incoming_data (self, data):
                self.echo_line += data
                
        def found_terminator (self):
                self.log (self.echo_line)
                self.echo_line = ''
 

# A manager interface for TCP/IP clients
        
class TCP_client (loginfo.Loginfo):
	
	TCP_CLIENT_CHANNEL = TCP_client_line
	
	def __init__ (self, timeout=60, precision=10):
		self.tcp_client_timeout = timeout
		self.tcp_client_precision = precision
		self.tcp_client_channels = {}
		
	def tcp_client (self, addr):
		try:
			return self.tcp_client_channels[addr]
			
		except KeyError:
			channel = self.tcp_client_channel (addr)
                        if channel.tcp_connect (addr, timeout):
                                return channel
                                
                        return
	
	def tcp_client_channel (self, addr):
                now = time.time ()
		channel = self.TCP_CLIENT_CHANNEL ()
                channel.tcp_client_key = addr
		async_limits.async_limit_recv (channel, now)
		async_limits.async_limit_send (channel, now)
                def handle_close ():
                        self.tcp_client_close (channel)
		channel.handle_close = handle_close
		self.tcp_client_channels[addr] = channel
		if len (self.tcp_client_channels) == 1:
	                assert None == self.log ('defer-start', 'debug')
			async_loop.async_schedule (
				time.time () + self.tcp_client_precision, 
				self.tcp_client_defer
				)
		return channel
		
	def tcp_client_defer (self, when):
                if self.tcp_client_channels:
	                for channel in self.tcp_client_channels.values ():
	                        self.tcp_client_inactive (channel, when)
                        return (
                                when + self.tcp_client_precision,
                                self.tcp_client_defer
                                ) # continue to defer
                
        	self.tcp_client_stop ()
                return None

	def tcp_client_inactive (self, channel, when):
		if not channel.closing and channel.connected and (
			when - max (
				channel.async_when_in, channel.async_when_out
				)
			) > self.tcp_client_timeout:
			assert None == channel.log ('inactive', 'debug')
			channel.handle_close ()

        def tcp_client_close (self, channel):
                assert None == channel.log (
                        'in="%d" out="%d"' % (
                                channel.async_bytes_in, 
                                channel.async_bytes_out
                                ),  'debug'
                        )
                channel.close ()
                del channel.recv, channel.send, channel.handle_close
                del self.tcp_client_channels[channel.tcp_client_key]

        def tcp_client_shutdown (self):
                for channel in self.tcp_client_channels.values ():
                        channel.close_when_done ()        
                        		
	def tcp_client_stop (self):
		assert None == self.log ('stop', 'debug')


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
	

class Pipeline (object):

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