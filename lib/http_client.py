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
	loginfo, finalization, async_chat, producer, collector, \
        tcp_client, dns_client, mime_headers, mime_reactor, http_reactor


class HTTP_client_reactor (
        mime_reactor.MIME_producer, finalization.Finalization
        ):
                
        mime_collector_headers = mime_collector_body = http_response = None
        
        def __init__ (
                self, pipeline, url, headers, command, body
                ):
                self.http_client_pipeline = pipeline
                self.http_urlpath = url
                self.http_command = command
                self.mime_producer_headers = headers
                self.mime_producer_body = body

        def __call__ (self, collect):
                self.mime_collector_body = collect
                self.http_client_pipeline.pipeline (self)
                del self.http_client_pipeline
                return self
                        

HTTP_RESPONSE_RE = re.compile ('.+?/([0-9.]+) ([0-9]{3}) (.*)')

class HTTP_client_pipeline (
	tcp_client.Pipeline, 
        mime_reactor.MIME_collector,
        tcp_client.TCP_client_channel,
	async_chat.Async_chat
	):

	"HTTP/1.0 keep-alive and HTTP/1.1 pipeline channel"

        def __init__ (self):
                async_chat.Async_chat.__init__ (self)
                tcp_client.Pipeline.__init__ (self)
                
        def __repr__ (self):
                return 'http-client-pipeline id="%x"' % id (self)

	# Asynchat
        
        terminator = '\r\n\r\n'
        
	def handle_connect (self):
		if self.pipeline_requests:
			self.pipeline_wake_up ()
		else:
			self.pipeline_sleeping = True
		
	# Pipeline
			
	def pipeline_error (self):
		# TODO: handle pipeline error
		if not self.pipeline_responses:
			# not resolved or not connected ...
			while self.pipeline_requests:
				reactor = self.pipeline_requests.popleft ()
				reactor.http_response = \
					'418 Unknown DNS host name'
		else:
			# broken connection ...
			tcp_pipeline.Pipeline.pipeline_error (self)
			
	def pipeline_wake_up (self):
		assert None == self.log ('wake-up-http-1.0', 'debug')
		# HTTP/1.0, push one at a time, maybe keep-alive or close
		# when done.
		#
		reactor = self.pipeline_requests.popleft ()
		if (
			self.pipeline_requests or
			self.pipeline_keep_alive
			):
			reactor.mime_producer_headers[
				'connection'
				] = 'Keep-alive'
		else:
			reactor.mime_producer_headers['connection'] = 'Close'
		self.http_client_continue (reactor)
		self.handle_write ()

	def pipeline_wake_up_11 (self):
		assert None == self.log ('wake-up-http-1.1', 'debug')
		# HTTP/1.1 pipeline, send all at once and maybe close when
		# done if not keep-aliver.
		#
		while True:
                        # push all request's reactors but the last one
                        #
			reactor = self.pipeline_requests.popleft ()
			reactor.mime_producer_headers[
				'connection'
				] = 'Keep-alive'
			if not self.pipeline_requests:
                                # close when done if empty and not kept alive
				if not self.pipeline_keep_alive:
					reactor.mime_producer_headers[
						'connection'
						] = 'Close'
				break
				
			self.http_client_continue (reactor)
		# push the last one and iniate send
		self.http_client_continue (reactor)
		self.handle_write ()
		
	# MIME collector

	def mime_collector_continue (self):
		reactor = self.pipeline_responses[0]
		try:
			(
				http_version, reactor.http_response
				) = self.mime_collector_lines.pop (
					0
					).split (' ', 1)
		except:
			self.http_collector_error ()
			return True

		if self.http_version == http_version[-3:]:
			if self.http_version == '1.1':
				self.pipeline_wake_up = \
					self.pipeline_wake_up_11
			self.http_version = http_version[-3:]
		if len (self.pipeline_requests) > 0:
			self.pipeline_wake_up ()
		reactor.mime_collector_headers = \
			self.mime_collector_headers = \
			mime_headers.map (self.mime_collector_lines)
		if (
			reactor.http_command == 'HEAD' or
			reactor.http_response[:3] in ('204', '304', '305')
			):
			self.pipeline_responses.pop ()
                else:
		        self.http_collector_continue (
                                reactor.mime_collector_body
                                )
                return False
		
	def mime_collector_finalize (self):
		self.pipeline_responses.pop ()
		if (
			len (self.pipeline_responses) == 0 and
			not self.pipeline_keep_alive
			):
                        self.close_when_done ()

	# HTTP/1.1

        http_version = '1.1'

	http_collector_continue = http_reactor.http_collector_continue

	http_collector_error = async_chat.Async_chat.handle_close

	# The HTTP client interface
        
        def GET (self, url, headers=None):
                return HTTP_client_reactor (
                        self, url, headers or {}, 'GET', None
                        )

        def http_client_continue (self, reactor):
                # push one or two producers in the output fifo ...
                line = '%s %s HTTP/%s\r\n' % (
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
                        self.producer_fifo.append (''.join (lines))
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
                                #        self.http_response or raise an 
                                #        exception?

                        lines = mime_headers.lines (
                                reactor.mime_producer_headers
                                )
                        lines.insert (0, line)
                        self.producer_fifo.append (''.join (lines))
                        self.producer_fifo.append (
                                reactor.mime_producer_body
                                )
                self.pipeline_responses.append (reactor)
                #
                # ready to send.


class HTTP_client (dns_client.TCP_client_DNS):

	TCP_CLIENT_CHANNEL = HTTP_client_pipeline

	def __call__ (self, host, port=80):
		channel = self.tcp_client ((host, port))
                if channel == None:
                        return

                if port == 80:
                        channel.http_host = host
                else:
                        channel.http_host = '%s:%d' % (host, port)
                return channel


if __name__ == '__main__':
        import sys
        from allegra import loginfo, async_loop, dns_client
        loginfo.log (
                'Allegra HTTP/1.1 Client'
                ' - Copyright 2005 Laurent A.V. Szyster'
                ' | Copyleft GPL 2.0', 'info'
                )
        try:
        	protocol, url = sys.argv[1].split ('//')
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
        HTTP_client () (
                addr[0], int(addr[1])
                ).GET (
        		'/' + path, {'Host': host}
        		) (collector.Loginfo_collector ())
        async_loop.loop ()
	#
	# Note:
	#
	# Network latency is usually so high that the DNS response will
	# come back long after the program entered the async_loop. So it is
	# safe to instanciate a named TCP pipeline and trigger asynchronous
	# DNS resolution before entering the loop.


# Note about this implementation
#
# The purpose of Allegra's HTTP/1.1 client is to provide peers with a
# simple and fully non-blocking API for all methods: GET, POST, HEAD,
# PUT, etc.
#
# Synopsis
#
#        from allegra import synchronizer, http_client
#        http = http_client.HTTP_client ()
#        request = http ('planet.python.org').GET ('/rss20.xml', {
#                'Host': 'planet.python.org',
#                'Accept-Charset': 'iso-8559-1,utf-8;q=0.9,ascii;q=0.8',
#                }) (synchronizer.Synchronized_open (
#                        'planet.python.org-rss20.xml', 'wb'
#                        ))
#