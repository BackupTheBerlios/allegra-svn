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

from allegra import (
	loginfo, finalization, async_chat, producer, collector, 
        tcp_client, dns_client, mime_headers, mime_reactor, http_reactor
        )


class HTTP_client_reactor (
        mime_reactor.MIME_producer, finalization.Finalization
        ):
                
        mime_collector_headers = http_response = None
        
        def __init__ (
                self, pipeline, url, headers, command, body
                ):
                self.http_pipeline = pipeline
                self.http_urlpath = url
                self.http_command = command
                self.mime_producer_headers = headers
                self.mime_producer_body = body

        def __call__ (self, collect):
                self.mime_collector_body = collect
                self.http_pipeline (self)
                self.http_pipeline = None
                return self
                        

# HTTP_RESPONSE_RE = re.compile ('.+?/([0-9.]+) ([0-9]{3}) (.*)')

class HTTP_client_pipeline (
	tcp_client.Pipeline, 
        mime_reactor.MIME_collector,
        tcp_client.TCP_client_channel,
	async_chat.Async_chat
	):

	"HTTP/1.0 keep-alive and HTTP/1.1 pipeline channel"
        
        # TODO: debug the HTTP/1.0 keep-alive fail-over
        #
        #       but the fact is that I don't have to right now ...
        #       HTTP/1.1 pipelining works very-well, thank you ;-)

        def __init__ (self):
                async_chat.Async_chat.__init__ (self)
                self.set_terminator ('\r\n\r\n')
                tcp_client.Pipeline.__init__ (self)
                
        def __repr__ (self):
                return 'http-client-pipeline id="%x"' % id (self)

        __call__ = tcp_client.Pipeline.pipeline

	# Asynchat
        
        ac_in_buffer_size = 1<<16 # 64KB input buffer
        ac_out_buffer_size = 4096 # 4KB output buffer

	def handle_connect (self):
		if self.pipeline_requests:
			self.pipeline_wake_up ()
		else:
			self.pipeline_sleeping = True
		
	# Pipeline

        pipeline_keep_alive = False
			
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
		# HTTP/1.0, push one at a time, maybe keep-alive or close
		# when done ...
		#
		reactor = self.pipeline_requests.popleft ()
		if (
			self.pipeline_requests or
			self.pipeline_keep_alive
			):
			reactor.mime_producer_headers[
				'connection'
				] = 'keep-alive'
		else:
			reactor.mime_producer_headers['connection'] = 'close'
		self.http_client_continue (reactor)
		# self.handle_write ()
                #
                # do not iniate send, wait for the write event instead

	def pipeline_wake_up_11 (self):
		# HTTP/1.1 pipeline, send all at once and maybe close when
		# done if not keep-aliver.
		#
                reactor = self.pipeline_requests.popleft ()
		while self.pipeline_requests:
                        # push all request's reactors
			reactor.mime_producer_headers[
				'connection'
				] = 'keep-alive'
                        self.http_client_continue (reactor)
                        reactor = self.pipeline_requests.popleft ()
		# push the last one
                if self.pipeline_keep_alive:
                        reactor.mime_producer_headers[
                                'connection'
                                ] = 'keep-alive'
                else:
                        # close when done and not kept alive
                        reactor.mime_producer_headers['connection'] = 'close'
		self.http_client_continue (reactor)
                # 
		# self.handle_write ()
		
	# MIME collector

	def mime_collector_continue (self):
                while (
                        self.mime_collector_lines and not 
                        self.mime_collector_lines[0]
                        ):
                        self.mime_collector_lines.pop (0)
                if not self.mime_collector_lines:
                        return False
                
		reactor = self.pipeline_responses[0]
		try:
			(
				http_version, reactor.http_response
				) = self.mime_collector_lines.pop (
					0
					).split (' ', 1)
		except:
                        assert None == self.log (
                                'invalid response line', 'debug'
                                )
			self.http_collector_error ()
			return True

                version = http_version[-3:]
                if (
                        version == '1.1' and 
                        self.pipeline_wake_up != self.pipeline_wake_up_11
                        ):
			self.pipeline_wake_up = self.pipeline_wake_up_11
                elif self.http_version != '1.0':
		        self.http_version = '1.0'
		reactor.mime_collector_headers = \
			self.mime_collector_headers = \
			mime_headers.map (self.mime_collector_lines)
		if (
			reactor.http_command == 'HEAD' or
			reactor.http_response[:3] in ('204', '304', '305')
			):
                        self.mime_collector_finalize ()
                else:
		        self.http_collector_continue (
                                reactor.mime_collector_body
                                )
                return False
		
	def mime_collector_finalize (self):
                # reset the channel state to collect the next request ...
                self.set_terminator ('\r\n\r\n')
                self.mime_collector_headers = \
                        self.mime_collector_lines = \
                        self.mime_collector_body = None
                # pop the reactor finalized 
                self.pipeline_responses.popleft ()
                self.http_responses += 1
                # wake up the pipeline if there are request pipelined
                if self.pipeline_requests:
                        self.pipeline_wake_up ()
                if not self.pipeline_responses:
                        self.pipeline_sleeping = True
                return False

	# HTTP/1.1 client reactor

        http_version = '1.1'

	http_collector_continue = http_reactor.http_collector_continue

	http_collector_error = async_chat.Async_chat.handle_close
        
        http_requests = http_responses = 0

        def http_client_continue (self, reactor):
                # push one string and maybe a producer in the output fifo ...
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
                        self.output_fifo.append (''.join (lines))
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
                        lines = mime_headers.lines (
                                reactor.mime_producer_headers
                                )
                        lines.insert (0, line)
                        self.output_fifo.append (''.join (lines))
                        self.output_fifo.append (
                                reactor.mime_producer_body
                                )
                # append the reactor to the queue of responses expected ...
                self.pipeline_responses.append (reactor)
                self.http_requests += 1
                #
                # ready to send.
                

class HTTP_client (dns_client.TCP_client_DNS):

	TCP_CLIENT_CHANNEL = HTTP_client_pipeline

	def __call__ (self, host, port=80, version='1.1'):
		channel = self.tcp_client ((host, port))
                if channel == None:
                        return

                if port == 80:
                        channel.http_host = host
                else:
                        channel.http_host = '%s:%d' % (host, port)
                channel.http_version = version
                return channel

        def tcp_client_close (self, channel):
                assert None == channel.log (
                        'requests="%d" responses="%d" '
                        'pending="%d" failed="%d"' % (
                                channel.http_requests, 
                                channel.http_responses,
                                len (channel.pipeline_requests),
                                len (channel.pipeline_responses)
                                ), 'debug'
                        )
                dns_client.TCP_client_DNS.tcp_client_close (self, channel)
        

def GET (pipeline, url, headers=None):
        if headers == None:
                headers = {'Host': pipeline.http_host}
        return HTTP_client_reactor (
                pipeline, url, headers, 'GET', None
                )
                
def POST (pipeline, url, body, headers=None):
        if headers == None:
                headers = {
                        'Host': pipeline.http_host, 
                        'Content-Type': 'application/x-www-form-urlencoded'
                        }
        return HTTP_client_reactor (
                pipeline, url, headers, 'POST', body
                )
                

# RE_URL = re.compile ('http://([^/:]+)[:]?([0-9]+)?(/.+)')