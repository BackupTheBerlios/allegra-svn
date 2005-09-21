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

from time import time

from allegra import async_loop
from allegra.loginfo import Loginfo
from allegra.pipeline import Pipeline
from allegra.async_limits import Async_limit_in, Async_limit_out

def TCP_client_pipeline (
	TCP_client_channel, Async_limit_in, Async_limit_out, Pipeline
	):

	pipeline_inactive = 60	# one minute timeout for inactive pipelines

	def __init__ (self, addr, requests=None, responses=None):
		Async_limit_in.__init__ (self)
		Async_limit_out.__init__ (self)
		TCP_client_channel.__init__ (self, addr)
		Pipeline.__init__ (self, requests, responses)
		self.async_limit_send ()
		self.async_limit_recv ()

	def handle_connect (self):
		self.log ('<connected/>')
		if len (self.pipeline_requests_fifo):
			self.pipeline_wake_up ()
		else:
			self.pipeline_sleeping = 1

	def pipeline_wake_up (self):
		# use that one for pipelining protocols, like HTTP/1.1
		while not self.pipeline_requests_fifo.is_empty ():
			reactor = self.pipeline_requests_fifo.pop ()
			self.push_with_producer (reactor)
			self.pipeline_responses_fifo.push (reactor)
		self.pipeline_sleeping = 1

	def pipeline_wake_up_once (self):
		# use this one for others, like HTTP/1.0
		if self.pipeline_requests_fifo.is_empty ():
			self.pipeline_sleeping = 1
		else:
			reactor = self.pipeline_requests_fifo.pop ()
			self.push_with_producer (reactor)
			self.pipeline_responses_fifo.push (reactor)
			self.pipeline_sleeping = 0

	def collect_incoming_data (self, data):
		if self.pipeline_responses_fifo.is_empty ():
			self.log ('<dropped-data bytes="%d"/>' % len (data))
			return

		self.pipeline_responses_fifo.first (
			).collect_incoming_data (data)

	def found_terminator (self):
		if self.pipeline_responses_fifo.is_empty ():
			self.log ('<dropped-terminator/>')
			return

		if self.pipeline_responses_fifo.first (
			).found_terminator ():
			self.pipeline_responses_fifo.pop ()
			self.pipeline_wake_up ()
			if self.pipeline_sleeping and not self.pipeline_keep_alive:
				self.handle_close ()

	def tcp_client_defer (self, when):
		if not self.closing and self.connected and (
			when - max (self.async_when_in, self.async_when_out)
			) > self.pipeline_inactive:
			self.log ('<inactive/>')
			self.handle_close ()


class TCP_client_pipeline_cache (Loginfo):

	Pipeline = None		# a Pipeline factory to override or subclass
	pipeline_precision = 1	# defered precision
	pipeline_resurect = 0	# resurect inactive pipeline

	def __init__ (self):
		self.pipeline_cache = {}

	def __repr__ (self):
		return '<tcp-client pipelines="%d"/>' % len (self.pipeline_cache)

	def pipeline_push (self, reactor, addr):
		(
			self.pipeline_cache.get (addr) or self.pipeline_init (addr)
			).pipeline_push (instance)

	def pipeline_init (self, addr, requests=None, responses=None):
		if not self.pipeline_cache:
			self.log ('<defered-start/>')
			async_loop.async_defer (
				time () + self.pipeline_precision,
				self.pipeline_defer
				)
		self.tcp_client_cache[addr] = pipeline = self.Pipeline (
			addr, requests, response
			)
		return pipeline

	def pipeline_delete (self, addr, pipeline):
		if (self.pipeline_resurect and not (
			pipeline.pipeline_requests_fifo.is_empty () and
			pipeline.pipeline_responses_fifo.is_empty () 
			)):
			self.pipeline_init (
				addr, pipeline.pipeline_merge ()
				)
		else:
			del self.pipeline_cache[addr]

	def pipeline_defer (self, when):
		for addr, pipeline in self.pipeline_cache.items ():
			pipeline.tcp_client_defer ()
			if pipeline.closing:
				self.pipeline_delete (addr, pipeline)
		if self.pipeline_cache:
			return (
				when + self.pipeline_precision,
				self.pipeline_defer
				) # continue to defer

		self.log ('<defered-stop/>')
		return None
