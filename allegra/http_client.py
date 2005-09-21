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

import re
from types import StringTypes

from allegra.producer import Simple_producer
from allegra.mime_reactor import MIME_reactor, mime_header_lines
from allegra.tcp_client import TCP_client_pipeline, TCP_client_pipeline_cache
from allegra.mime_collector import MIME_collector, mime_headers_split, mime_headers_map
from allegra.http_collector import HTTP_collector


HTTP_RESPONSE_RE = re.compile ('.+?/([0-9.]+) ([0-9]{3}) (.*)')

class HTTP_client_pipeline (TCP_client_pipeline, MIME_collector, HTTP_collector):

	"HTTP/1.0 keep-alive and HTTP/1.1 pipeline channel"

        terminator = '\r\n\r\n'
	http_version = '1.1'

	def pipeline_wake_up (self):
		# HTTP/1.0 keep-alive
		reactor = self.pipeline_requests_fifo.pop ()
		if (
			self.pipeline_requests_fifo.is_empty () and
			not self.pipeline_keep_alive
			):
			reactor.mime_producer_headers['connection'] = 'Close'
		else:
			reactor.mime_producer_headers['connection'] = 'Keep-alive'
		self.http_client_pipeline_push (reactor)

	def pipeline_wake_up_11 (self):
		# HTTP/1.1 pipeline
		while 1:
			reactor = self.pipeline_requests_fifo.pop ()
			if (
				self.pipeline_requests_fifo.is_empty () and
				not self.pipeline_keep_alive
				):
				reactor.mime_producer_headers['connection'] = 'Close'
				self.http_client_pipeline_push (reactor)
				break
			
			else:
				reactor.mime_producer_headers['connection'] = 'Keep-alive'
				self.http_client_pipeline_push (reactor)

	def pipeline_push (self, reactor):
		line = '%s %s HTTP/%s' % (
			reactor.http_command, reactor.http_urlpath, self.http_version
			)
		if reactor.mime_producer_body != None:
			# POST and PUT
			if self.http_version == '1.1':
				reactor.mime_producer_body = Chunked_producer (
					reactor.mime_producer_body
					)
				reactor.mime_producer_headers['transfer-encoding'] = 'chunked'
			elif hasattr (reactor, 'content_length'):
				reactor.mime_producer_headers['content-length'] = str(
					reactor.content_length ()
					)
			else:
				return
				#
				# TODO: add an error condition in self.http_response
				#       or raise an exception?

			self.producer_fifo.push (Simple_producer ('\r\n'.join (
				mime_header_lines (reactor.mime_producer_headers, [line])
				)))
			self.producer_fifo.push (reactor.mime_producer_body)
		else:
			# GET, HEAD, ...
			self.producer_fifo.push (Simple_producer ('\r\n'.join (
				mime_header_lines (reactor.mime_producer_headers, [line])
				)))
		self.initiate_send ()
		self.pipeline_responses_fifo.push (reactor)

	def mime_collector_continue (self):
		reactor = self.pipeline_responses_fifo.first ()
		try:
			(
				http_version, reactor.http_response
				) = self.mime_collector_lines.pop (0).split (' ', 1)
		except:
			self.http_collector_error ()
			return 0

		if self.http_version == http_version[-3:]:
			if self.http_version == '1.1':
				self.pipeline_wake_up = self.pipeline_wake_up_11
			self.http_version = http_version[-3:]
		if not self.pipeline_requests_fifo.is_empty ():
			self.pipeline_wake_up ()
		reactor.mime_collector_headers = self.mime_collector_headers = \
			mime_headers_map (self.mime_collector_lines)
		if (
			reactor.http_command == 'HEAD' or
			reactor.http_response[:3] in ('204', '304', '305')
			):
			self.pipeline_responses_fifo.pop ()
			return 0

		return self.http_collector_continue (reactor)

	http_collector_error = TCP_client_pipeline.handle_close
	# 	close the channel when there's a problem in the HTTP collector!

	def mime_collector_finalize (self, collector):
		reactor = self.pipeline_responses_fifo.pop ()
		if (
			self.pipeline_responses_fifo.is_empty () and
			not self.pipeline_keep_alive
			):
			self.producer_fifo.push (None)

	def tcp_client_dns_error (self, reactor):
		reactor.http_response = '418 Unknown DNS host name'


class HTTP_client_interface:

	def http_client_reactor (self, url, headers, command):
                reactor = MIME_reactor ()
                reactor.http_command = command
                reactor.http_urlpath = url
                reactor.mime_producer_headers = headers
                reactor.__call__ = (
                        lambda instance=None, me=self, r=reactor:
                                me.http_client_reactor_continue (r, instance)
                        )
                return reactor

	def http_client_reactor_continue (self, reactor, instance=None):
		del reactor.__call__
		#	break the circular reference between the reactor and
		#	the channel via the client cache
                if instance != None:
			http_client_reactor_body (reactor, instance)
                self.pipeline_push (reactor)
		return reactor
		#
		# return the method bounded instance, so that calling the
		# instance is equivalent to retrieving its reference, making
		# a nice syntax possible when chaining reactors

	def http_client_reactor_body (self, reactor, instance):
		if reactor.http_command not in ('POST', 'PUT'):
			reactor.http_command = 'POST'
		if has_attr (instance, 'mime_collector_headers'):
			# allow to chain MIME reactors
			reactor.mime_producer_headers.update (
				instance.mime_collector_headers
				)
			reactor.mime_producer_body = instance
		elif hasattr (instance, 'producer_stalled'):
			# accept stallable producers as HTTP body
			reactor.mime_producer_body = instance
		elif isinstance (instance, StringTypes):
			# and accept strings too
			if len (instance) < 1<<16:
				reactor.mime_producer_body = Simple_producer (
					instance
					)
			else:
				reactor.mime_producer_body = Scanning_producer (
					instance
					)
		else:
			raise Error (
				'MIME reactors must be called with a string, '
				'or a stallable producer as unique argument.'
				)
			

class HTTP_proxy_client (HTTP_client_interface, HTTP_client_pipeline):

	def http (self, url, headers={}, command='GET'):
		if url[:2] == '//':
			url = 'http:' + url
			headers['host'] = url[2:].split ('/', 1)[0]
		else:
			url = 'http://127.0.0.1' + url
			headers['host'] = '127.0.0.1'
		return self.http_client_reactor (url, headers, command)


class HTTP_client_pipeline_cache (HTTP_client_interface, TCP_client_pipeline_cache):

	timeouts_time = 5
	timeouts_precision = 0.5
	pipeline_keep_alive = 1

	def http (self, url, headers={}, command='GET'):
		if url[:2] == '//':
			headers['host'], url = url[2:].split ('/', 1)[0]
		else:
			headers['host'] = '127.0.0.1'
                reactor = self.http_client_reactor (url, headers, command)
                reactor.tcp_client_key = host
                return reactor

	def Pipeline (self, key):
		if key.find (':') > -1:
			host, port = key.split (':')
			return HTTP_client_pipeline (host, port, self)
		
		else:
			return HTTP_client_pipeline (key, 80, self) 
		

def HTTP_client (proxy=None, port=3128):
	if proxy != None:
		return HTTP_proxy_client (proxy, port)

	return HTTP_client_pipeline_cache ()


#--- command line interface

if __name__ == '__main__':
	import asyncore
	from allegra.monitor_server import monitor_server
	monitor_server ()
	asyncore.loop (1.0)
			
"""
allegra/http_client.py

an asynchronous HTTP client library with support for HTTP/1.0
keep-alive and HTTP/1.1 pipelining, asynchronous caching, finalization
timeouts and loginfo.

the principal interface is the 'http' factory function. it returns a
reactor instance with a finalization interface. the reactor can be
pushed onto the producer fifo of a stallable asynchronous channel, or
it may be called with a string, a producer or a reactor as unique
argument, then finalyzed.

write

	from http_client import http
	
	http ('//host/urlpath/post') (
		http ('//host/urlpath/get') ()
		)

if you were to collect data from the web and post it to a web server,
with both channel open in parallel. the http function is a factory that
returns a reactor. see reactors.py for more information about them.

if you require a strict sequence in operations, use the finalization
interface and write:

	http ('//host/urlpath/get') ().finalization = http (
		'//host/urlpath/post'
		)

or maybe more clearly, using a continuation:

	from continuation import Continue
	Continue ([
		http ('//host/urlpath/get'),
		http ('//host/urlpath/post')
		]) ()

you may chain other type of reactors, like file or mail reactors

to save the Google home page, write:

	from allegra.aio import fs
	fs ('~/archive/www.google.com/index.html') (
		http ('//www.google.com/') ()
		)

to send it by mail, write:

	from allegra.aio import smtp
	smtp (['laurent.szyster@q-survey.be',]) (
		http ('//www.google.com/') ()
		)

if you want to do both at the same time:

	from allegra.aio import split
	split (
		http ('//www.google.com/') (), [
			mailto ('laurent.szyster@q-survey.be'),
			fs ('~/archive/www.google.com/index.html')
			]
		)

the writing may seem awkward at first, but it is the only simple one
to program asynchronous network clients from a Python console.

HTTP_client is intended to cache and manage HTTP pipelines and relieve
the developper (me!) from networking chore about timeouts, broken
connection and more. any request submitted via the HTTP_client will
either fail or succeed, but none will hang or block.


How does it works?

the mechanic at work is the following: each request is instanciated as
a mime reactor and pushed into a HTTP client pipeline. the reactor can
be immediately pushed as a producer in a channel that supports stalled
producers. if it is not referenced elswhere, the reactor will finalize
itself when the response is complete and the reactor popped out of the
HTTP pipeline response fifo.

"""
