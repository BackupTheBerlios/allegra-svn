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

import re, types

from allegra import \
	producer, tcp_pipeline, mime_headers, mime_reactor, http_reactor


HTTP_RESPONSE_RE = re.compile ('.+?/([0-9.]+) ([0-9]{3}) (.*)')

class HTTP_client_pipeline (
	tcp_pipeline.TCP_pipeline, mime_reactor.MIME_collector
	):

	"HTTP/1.0 keep-alive and HTTP/1.1 pipeline channel"

        terminator = '\r\n\r\n'
	http_version = '1.1'

	def pipeline_error (self):
		# TODO: handle pipeline error
		if self.pipeline_responses_fifo.is_empty ():
			# not resolved or not connected ...
			while not self.pipeline_requests.is_empty ():
				reactor = self.pipeline_requests.pop ()
				reactor.http_response = \
					'418 Unknown DNS host name'
		else:
			# broken connection ...
			tcp_pipeline.TCP_pipeline.pipeline_error (self)
			
	def pipeline_wake_up (self):
		# HTTP/1.0, push one at a time, maybe keep-alive or close
		# when done.
		#
		reactor = self.pipeline_requests.pop ()
		if (
			self.pipeline_requests.is_empty () and
			not self.pipeline_keep_alive
			):
			reactor.mime_producer_headers['connection'] = 'Close'
		else:
			reactor.mime_producer_headers[
				'connection'
				] = 'Keep-alive'
		self.http_producer_continue (reactor)
		self.handle_write ()

	def pipeline_wake_up_11 (self):
		# HTTP/1.1 pipeline, send all at once and maybe close when
		# done if not keep-aliver.
		#
		while 1:
			reactor = self.pipeline_requests.pop ()
			reactor.mime_producer_headers[
				'connection'
				] = 'Keep-alive'
			if self.pipeline_requests.is_empty ():
				if not self.pipeline_keep_alive:
					reactor.mime_producer_headers[
						'connection'
						] = 'Close'
				break
				
			# push all request's reactors but the last one
			#
			self.http_client_push (reactor)
		# push the last one, maybe close when done, and iniate send
		#
		self.http_producer_continue (reactor)
		self.handle_write ()

	def mime_collector_continue (self):
		reactor = self.pipeline_responses_fifo.first ()
		try:
			(
				http_version, reactor.http_response
				) = self.mime_collector_lines.pop (
					0
					).split (' ', 1)
		except:
			self.http_collector_error ()
			return False

		if self.http_version == http_version[-3:]:
			if self.http_version == '1.1':
				self.pipeline_wake_up = \
					self.pipeline_wake_up_11
			self.http_version = http_version[-3:]
		if not self.pipeline_requests.is_empty ():
			self.pipeline_wake_up ()
		reactor.mime_collector_headers = \
			self.mime_collector_headers = \
			mime_headers.map (self.mime_collector_lines)
		if (
			reactor.http_command == 'HEAD' or
			reactor.http_response[:3] in ('204', '304', '305')
			):
			self.pipeline_responses.pop ()
			return False

		return self.http_collector_continue (reactor)
		
	def mime_collector_finalize (self, collector):
		self.pipeline_responses.pop ()
		if (
			self.pipeline_responses.is_empty () and
			not self.pipeline_keep_alive
			):
			self.producer_fifo.push (None)

	# close the channel when there is an in the HTTP collector!
	#
	http_collector_error = tcp_pipeline.TCP_pipeline.handle_close

	http_collector_continue = http_reactor.http_collector_continue

	def http_producer_continue (self, reactor):
		# push one or two producers in the output fifo ...
		line = '%s %s HTTP/%s' % (
			reactor.http_command, 
			reactor.http_urlpath, 
			self.http_version
			)
		if reactor.mime_producer_body == None:
			# GET, HEAD, DELETE, ...
			#
			lines = mime_headers.lines (
				reactor.mime_producer_headers
				)
			lines.insert (0, line)
			self.producer_fifo.push (
				producer.Simple_producer (''.join (lines))
				)
		else:
			# POST and PUT ...
			#
			if self.http_version == '1.1':
				reactor.mime_producer_body = \
					http_reactor.Chunk_producer (
						reactor.mime_producer_body
						)
				reactor.mime_producer_headers[
					'transfer-encoding'
					] = 'chunked'
			elif hasattr (reactor, 'content_length'):
				reactor.mime_producer_headers[
					'content-length'
					] = str (reactor.content_length ())
			else:
				return
				#
				# TODO: add an error condition in 
				#	self.http_response or raise an 
				#	exception?

			lines = mime_headers.lines (
				reactor.mime_producer_headers
				)
			lines.insert (0, line)
			self.producer_fifo.push (
				producer.Simple_producer (''.join (lines))
				)
			self.producer_fifo.push (reactor.mime_producer_body)
		self.pipeline_responses.push (reactor)
		#
		# ready to send.

	def http_client_reactor (self, url, headers, command):
                reactor = mime_reactor.MIME_reactor (headers)
                reactor.http_command = command
                reactor.http_urlpath = url
                reactor.mime_producer_headers = headers
		reactor.mime_producer_headers['host'] = self.http_host
                def react (instance=None):
                	self.http_client (reactor, instance)
                reactor.__call__ = react
                return reactor

	def http_client (self, reactor, instance):
		# break the circular reference between the reactor and
		# the channel via the client cache
		del reactor.__call__
		# push HEAD, GET, DELETE requests without further process
                if instance == None:
                	assert reactor.http_command in (
                		'HEAD', 'GET', 'DELETE'
                		)
	                self.pipeline_push (reactor)
			return reactor

		assert reactor.http_command in ('POST', 'PUT')
		
		if has_attr (instance, 'mime_collector_headers'):
			# chain MIME reactors
			reactor.mime_producer_headers.update (
				instance.mime_collector_headers
				)
			reactor.mime_producer_body = instance
		elif hasattr (instance, 'producer_stalled'):
			# accept stallable producers as HTTP body
			reactor.mime_producer_body = instance
		elif isinstance (instance, types.StringTypes):
			# as well as 8-bit and UNICODE strings
			reactor.mime_producer_body = \
				producer.Simple_producer (instance)
		else:
			raise Error (
				'MIME reactors must be called with a string,'
				' or a stallable producer as unique argument.'
				)
				
                self.pipeline_push (reactor)
		return reactor
		#
		# return the method bounded instance, so that calling the
		# instance is equivalent to retrieving its reference, making
		# a nice syntax possible when chaining reactors
			
	# The AIO Interface:
	#
	#	aio.http ('host').POST ('/form.cgi') (
	#		'urlencoded-form-data'
	#		)

	def HEAD (self, url, headers={}):
                return self.http_client_reactor (url, headers, 'HEAD')		
		
	def DELETE (self, url, headers={}):
                return self.http_client_reactor (url, headers, 'DELETE')		
		
	def GET (self, url, headers={}):
                return self.http_client_reactor (url, headers, 'GET')		
		
	def POST (self, url, headers={}):
                return self.http_client_reactor (url, headers, 'POST')
		
	def PUT (self, url, headers={}):
                return self.http_client_reactor (url, headers, 'PUT')
		
		
class HTTP_client (tcp_pipeline.TCP_pipeline_cache):

	Pipeline = HTTP_client_pipeline

	def pipeline_init (self, addr):
		pipeline = tcp_pipeline.TCP_pipeline_cache.pipeline_init (
			self, addr
			)
                if addr[1] == 80:
			pipeline.http_host = addr[0]
         	else:
			pipeline.http_host = '%s:%d' % addr
		return pipeline
	
	def http (self, host, port=80):
		return self.pipeline_get ((host, port))
	

if __name__ == '__main__':
        import sys
        from allegra import loginfo, async_loop, dns_client
        loginfo.log (
                'Allegra HTTP/1.1 Client'
                ' - Copyright 2005 Laurent A.V. Szyster'
                ' | Copyleft GPL 2.0', 'info'
                )
        try:
        	command, url = sys.argv[1:]
        	protocol, url = url.split ('//')
        	host, path = url.split ('/', 1)
        	addr = host.split (':')
        	if len (addr) < 2:
        		addr.append ('80')
 	except:
 		sys.exit (1)
 	
 	# get a TCP pipeline connected to the address extracted from the
 	# URL and push an HTTP reactor with the given command and URL path,
 	# close when done ...
 	#
        HTTP_client (
        	dns_client.DNS_client (dns_client.dns_servers ())
        	).http (
        		addr[0], int (addr[1])
        		).http_client_reactor (
        			'/' + path, {}, command
        			) (async_loop.loginfo.Loginfo_collector ())
        async_loop.loop ()
	#
	# Note:
	#
	# Network latency is usually so high that the DNS response will
	# come back long after the program entered the async_loop. So it is
	# safe to instanciate a named TCP pipeline and trigger asynchronous
	# DNS resolution before entering the loop.

"""
http_client.py

An Asynchronous HTTP/1.1 Client Pipeline

The module http_client.py implements is an asynchronous HTTP client 
with support for HTTP/1.0 keep-alive and HTTP/1.1 pipelining, asynchronous 
caching, finalization, timeouts and loginfo. The purpose is to integrate
a simple and reliable client interface in Allegra's library.

HTTP_client is intended to cache and manage HTTP pipelines and relieve
web peer developers from networking chore about timeouts, broken
connection and more. Any request submitted via the HTTP_client will
either fail or succeed, but none will hang or block.

The principal interface is the 'http' factory function. It returns
an HTTP pipeline from a cache (or the proxy's pipeline) with the 
following factories:
	
	get, head, del, post, put, ...

that return a reactor instance with a finalization interface. 

This reactor can be pushed onto the producer fifo of a stallable asynchronous 
channel, or it may be called with a string, a producer or a reactor as unique
argument, then finalyzed.

the mechanic at work is the following: each request is instanciated as
a mime reactor and pushed into a HTTP client pipeline. the reactor can
be immediately pushed as a producer in a channel that supports stalled
producers. if it is not referenced elswhere, the reactor will finalize
itself when the response is complete and the reactor popped out of the
HTTP pipeline response fifo.

Write

	from allegra.aio import http
	
	http ('dest').POST ('/urlpath/post.cgi') (
		http ('source').GET ('/urlpath/get.html') ()
		)

to collect data from the web and post it to a web server, with both channel 
open in parallel.  If you require a strict sequence in operations, use the 
finalization interface instead, and write:

	http ('source').GET ('/urlpath/get.html') (
		).finalization = http ('dest').POST ('/urlpath/post.cgi')

or maybe more clearly, using a continuation:

	from allegra.finalization import Continue
	
	Continue ([
		http ('source').GET ('/urlpath/get.html'),
		http ('dest').POST ('/urlpath/post.cgi')
		]) ()

you may chain other type of reactors, like file or mail reactors.

To save the Google's home page (or error message), write:

	from allegra.aio import fs
	
	fs ('~').write ('/archive/www.google.com/index.html') (
		http ('www.google.com').GET ('/') ()
		)

To send the same web page by mail via the local relay, write:

	from allegra.aio import mailto
	
	mailto (('laurent.szyster@q-survey.be',)) (
		http ('www.google.com').GET ('/') ()
		)

And if you want to do both at the same time, without queuing:

	from allegra.aio import atee
	atee (http ('www.google.com').GET ('/'), (
		mailto (('laurent.szyster@q-survey.be',)),
		fs ('~').write (
			'/archive/www.google.com/index.html'
			)
		)) ()

The writing may seem awkward at first, but it is the only simple one
to program asynchronous network clients from a Python console.

Let's write it line by line instead:

	from allegra.aio import http
	
	dest_POST = http ('dest').POST ('/urlpath/post.cgi')
	source_GET = http ('source').GET ('/urlpath/get.html')

and multiplex

	dest_POST (source_GET ())

But if you use a finalization to chain

	source_GET ().finalization = dest_POST
	
the page with not be posted, because there is still a reference to
the source_get instance and it will not finalize. It is not an ugly
bug but a remarkable feature, a reliable and convenient way to set 
breakpoints in an asynchronous workflow.

To debug it as it is written: at the interpreter's prompt.


"""
