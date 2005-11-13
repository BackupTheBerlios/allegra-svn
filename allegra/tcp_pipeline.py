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

import time

from allegra import loginfo, async_loop, tcp_client #, fifo


class TCP_pipeline (tcp_client.TCP_client_channel):

	pipeline_sleeping = False
	pipeline_keep_alive = False

	def __init__ (self, requests=None, responses=None):
		self.pipeline_requests = requests or fifo.FIFO_deque ()
		self.pipeline_responses = responses or fifo.FIFO_deque ()
		tcp_client.TCP_client_channel.__init__ (self)

	def handle_connect (self):
		assert None == self.log ('connected', 'debug')
		if len (self.pipeline_requests):
			self.pipeline_wake_up ()
		else:
			self.pipeline_sleeping = True

	def collect_incoming_data (self, data):
		if self.pipeline_responses.is_empty ():
			self.log (
				'dropped-data bytes="%d"' % len (data), 
				'error'
				)
			return

		self.pipeline_responses.first (
			).collect_incoming_data (data)

	def found_terminator (self):
		if self.pipeline_responses.is_empty ():
			self.log ('dropped-terminator', 'error')
			return

		if self.pipeline_responses.first (
			).found_terminator ():
			self.pipeline_responses.pop ()
			self.pipeline_wake_up ()
			if (
				self.pipeline_sleeping and 
				not self.pipeline_keep_alive
				):
				self.handle_close ()

	def dns_resolve (self, request):
		if len (request.dns_resources) > 0:
			# DNS address resolved, connect ...
			self.tcp_connect ((
				request.dns_resources[0], 
				self.tcp_client_port
				))
			return
			
		self.pipeline_error ()
		
	def pipeline_error (self):
		while not self.pipeline_requests.is_empty ():
			self.pipeline_requests.pop ()
			
		while not self.pipeline_responses.is_empty ():
			self.pipeline_responses.pop ()
						
	def pipeline_push (self, request):
		self.pipeline_requests.push (request)
		if self.pipeline_sleeping:
			self.pipeline_sleeping = False
			self.pipeline_wake_up ()

	def pipeline_wake_up (self):
		# pipelining protocols, like HTTP/1.1 or ESMPT
		while not self.pipeline_requests.is_empty ():
			reactor = self.pipeline_requests.pop ()
			self.producer_fifo.append (reactor)
			self.pipeline_responses.push (reactor)
		self.pipeline_sleeping = True

	def pipeline_wake_up_once (self):
		# synchronous protocols, like HTTP/1.0 or SMTP
		if self.pipeline_requests.is_empty ():
			self.pipeline_sleeping = True
		else:
			reactor = self.pipeline_requests.pop ()
			self.producer_fifo.append (reactor)
			self.pipeline_responses.push (reactor)
			self.pipeline_sleeping = False

	def pipeline_merge (self):
		if self.pipeline_requests.is_empty ():
			if self.pipeline_responses.is_empty ():
				return None
			
			else:
				return self.pipeline_responses
			
		else:
			if self.pipeline_responses.is_empty ():
				return self.pipeline_requests
			
			else:
				fifo = fifo.FIFO_pipeline ()
				fifo.push_fifo (self.pipeline_responses)
				fifo.push_fifo (self.pipeline_requests)
				return fifo


def is_ip (host):
	try:
		return len ([
			n for n in host.split ('.') 
			if -1 < int (n) < 255
			]) == 4
				
	except:
		return False

class TCP_pipeline_cache (loginfo.Loginfo):

	TCP_PIPELINE = None # a Pipeline factory to override or subclass
	
	pipeline_precision = 3	# defered every 3 seconds (large)
	pipeline_resurect = 0	# don't resurect inactive pipeline

	def __init__ (self, dns_client=None):
		self.pipeline_cache = {}
		self.dns_client = dns_client

	def __repr__ (self):
		return 'tcp-client id="%x"' % id (self)
			
	def pipeline_get (self, addr):
		return (
			self.pipeline_cache.get (addr) or 
			self.pipeline_init (addr)
			)

	def pipeline_push (self, reactor, addr):
		self.pipeline_get (addr).pipeline_push (reactor)

	def pipeline_init (self, addr):
		if not self.pipeline_cache:
			# empty cache, defer a recurrent tcp session event
			assert None == self.log ('defered-start', 'debug')
			async_loop.async_schedule (
				time.time () + self.pipeline_precision,
				self.pipeline_defer
				)
		# cache a disconnected pipeline
		self.pipeline_cache[addr] = pipeline = self.TCP_PIPELINE ()
		if is_ip (addr[0]):
			# connect to *any* IP address and TCP port
			pipeline.tcp_connect (addr)
		else:
			# resolve what must be a DNS host name ...
			pipeline.tcp_client_port = addr[1]
			self.dns_client.dns_resolve (
				(addr[0], 'A'), pipeline.dns_resolve
				)
		return pipeline
		
	def pipeline_delete (self, addr, pipeline):
		# TODO: handle this cleaner ...
		#
		if (self.pipeline_resurect and not (
			pipeline.pipeline_requests.is_empty () and
			pipeline.pipeline_responses.is_empty () 
			)):
			self.pipeline_init (
				addr, pipeline.pipeline_merge ()
				)
		else:
			del self.pipeline_cache[addr]

	def pipeline_defer (self, when):
		for addr, pipeline in self.pipeline_cache.items ():
			# pipeline.tcp_client_defer ()
			if pipeline.closing:
				self.pipeline_delete (addr, pipeline)
		if len (self.pipeline_cache) > 0:
			return (
				when + self.pipeline_precision,
				self.pipeline_defer
				) # continue to defer

		assert None == self.log ('defered-stop', 'debug')


# Note about this implementation
#
# The first class, TCP_pipeline, is a generic implemention that 
# supports pipelining for HTTP/1.0 and HTTP/1.1, SMTP and ESMTP, etc.
# It is complete with I/O limits, connection and zombie timeouts.
#
# The actual API is provided by the second class, which manages a cache
# of TCP pipelines and from which to derive TCP user agents like a web
# proxy, a news reader or a mailer. This class also handle the chore of
# name resolution (using a subset of the PNS model, more to come ...).
#
# The purpose is to manage I/O appropriately and minimize the TCP overhead
# whenever possible by reducing the number of concurrent connections, even
# if the communication protocol does not support pipelining. Allegra's
# TCP pipelines also have limits because peer applications must be able
# to measure and rationate the bandwith they use.
#
# A TCP pipeline cache also handles DNS name resolution for its accessors
# which mitigate its effect, allowing to have more than one connection for
# each address (ip, port) if they have distinct names. Practically, you want
# to multiplex parallel independant requests to different namespaces on
# the web even if they are actually served by the same IP address. Client
# connections are defacto rationated on a service base.
#
# All Allegra TCP clients are built as pipeline cache, managing dictionnaries
# of named and/or addressed TCP sessions, handling finalized reactors through 
# their pipes for independant asynchronous accessors.
#

# Note about this implementation
#
# This pipeline class implements a usefull function for TCP protocols like
# HTTP or SMTP that eventually support pipelining, but may not (HTTP/1.0 and
# many broken mail relays). It provides a pipelining interface for allegra's
# clients even when the server does not support it, buffering locally what
# cannot be buffered to the network.
#
# Moreover, this class allow to handles broken TCP pipelines gracefully,
# pushing back up front the requests allready sent (provided of course that
# they can re-produce the original request, for instance an GET HTTP request
# and its MIME headers).
#
# Because what you want from a pipeline is to abstract the communication
# channel up to a point where it is resilient and allways returns a result,
# something or NULL. In the case of an HTTP pipeline client, like a proxy,
# a REST gateway or an RSS reader, what matters is that the accessor is
# provided with a response. It may be a "HTTP/1.1 418 DNS error", a "404"
# or an invalid XML string, as long as it does not raise an exception or
# stall for ever it does the job.
#
# MIME Protocols
#
# Most Internet Application Protocols (HTTP, SMTP, POP, NNRP, NNTP, 
# MULTIPART, SMIME, HTTPS, Gnutella, SOAP, XML/RPC, etc) are MIME 
# protocols of TCP pipelines such as:
#
# 	Request Line
#	Optional MIME headers
#	
#	Optional MIME body
#
#	Response Line
#	Optional MIME headers
#	
#	Optional MIME body
#	
# It does payoff to refactor that implementation in a base class for
# client TCP pipeline channel and a MIME reactor classes, because it allows 
# to use the same interfaces for derived channel classes and chain the same
# MIME reactors finalization together to form asynchronous pipes. 
#
# Effectively, an HTTP request  reactor can be finalized as the body of a 
# SMTP post or set as its body producer, because both are actually MIME 
# pipeline reactors.
#
# MIME reactors and TCP pipelines also integrate well with Allegra's 
# asynchronous MIME servers, like http_server.py and smtp_server.py, 
# making it possible for PRESTo developers to program and debug a 
# multi-protocol workflow from the web prompt.
#