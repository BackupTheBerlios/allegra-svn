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

import socket

from allegra import (
	loginfo, finalization,
        async_chat, producer, collector, async_client,
        tcp_client, mime_headers, mime_reactor, http_reactor
        )


class Request (finalization.Finalization):
                
        http_response = mime_collector_headers = mime_collector_body = None
        
        def __init__ (
                self, pipeline, url, headers, command, body
                ):
                headers ['Host'] = pipeline.http_host
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
                        

class Pipeline (
        mime_reactor.MIME_collector,
	async_chat.Dispatcher, 
        async_client.Pipeline
	):

	"HTTP/1.0 keep-alive and HTTP/1.1 pipeline channel"
        
        ac_in_buffer_size = 1<<16 # 64KB input buffer
        ac_out_buffer_size = 4096 # 4KB output buffer

        def __init__ (self):
                async_chat.Dispatcher.__init__ (self)
                self.set_terminator ('\r\n\r\n')
                self.pipeline_set ()
                
        def __repr__ (self):
                return 'http-client-pipeline id="%x"' % id (self)

        def __call__ (self, request):
                "pipeline a new request, wake up if sleeping"
                self.pipeline_requests.append (request)
                if not self.pipeline_responses:
                        self.pipeline_wake_up ()
                
	# async_chat
        
	def handle_connect (self):
                if self.pipeline_requests and not self.pipeline_responses:
			self.pipeline_wake_up ()

        def handle_close (self):
                assert None == self.log (
                        'pipelined '
                        ' requests="%d" responses="%d"'
                        ' pending="%d" failed="%d"' % (
                                self.http_requests, 
                                self.http_responses,
                                len (self.pipeline_requests),
                                len (self.pipeline_responses)
                                ), 'debug'
                        )
		self.close ()
                
	# pipeline

        def pipeline_wake_up (self):
                if self.http_version == '1.1' and self.http_responses:
                        self.pipeline_wake_up_11 ()
                else:
                        self.pipeline_wake_up_10 ()
                        
	def pipeline_wake_up_10 (self):
		# HTTP/1.0, push one at a time, maybe keep-alive or close
		# when done ...
		#
		request = self.pipeline_requests.popleft ()
		if (
			self.pipeline_requests or
			self.pipeline_keep_alive
			):
			request.mime_producer_headers[
				'connection'
				] = 'keep-alive'
		else:
			request.mime_producer_headers['connection'] = 'close'
		self.http_client_continue (request)

	def pipeline_wake_up_11 (self):
		# HTTP/1.1 pipeline, send all at once and maybe close when
		# done if not keep-aliver.
		#
                request = self.pipeline_requests.popleft ()
		while self.pipeline_requests:
                        # push all request's reactors
			request.mime_producer_headers[
				'connection'
				] = 'keep-alive'
                        self.http_client_continue (reactor)
                        request = self.pipeline_requests.popleft ()
		# push the last one
                if self.pipeline_keep_alive:
                        request.mime_producer_headers[
                                'connection'
                                ] = 'keep-alive'
                else:
                        # close when done and not kept alive
                        request.mime_producer_headers['connection'] = 'close'
		self.http_client_continue (request)
 		
	# MIME collector

	def mime_collector_continue (self):
                while (
                        self.mime_collector_lines and not 
                        self.mime_collector_lines[0]
                        ):
                        self.mime_collector_lines.pop (0)
                if not self.mime_collector_lines:
                        return self.closing
                        #
                        # make sure that the collector is stalled once the
                        # dispatcher has been closed.
                
		request = self.pipeline_responses[0]
		try:
			(
				http_version, request.http_response
				) = self.mime_collector_lines.pop (
					0
					).split (' ', 1)
		except:
                        assert None == self.log (
                                'invalid response line', 'debug'
                                )
			self.http_collector_error ()
			return True

                self.http_version = http_version[-3:]
		request.mime_collector_headers = \
			self.mime_collector_headers = \
			mime_headers.map (self.mime_collector_lines)
		if (
			request.http_command == 'HEAD' or
			request.http_response[:3] in ('204', '304', '305')
			):
                        self.mime_collector_finalize ()
                else:
		        self.http_collector_continue (
                                request.mime_collector_body
                                )
                return self.closing # stall the collector if closing
		
	def mime_collector_finalize (self):
                # wake up the pipeline if there are request pipelined
                # and that the connection is kept alive
                if (
                        self.pipeline_requests and 
                        self.mime_collector_headers.get (
                                'connection'
                                ) == 'keep-alive'
                        ):
                        self.pipeline_wake_up ()
                # reset the channel state to collect the next request ...
                self.set_terminator ('\r\n\r\n')
                self.mime_collector_headers = \
                        self.mime_collector_lines = \
                        self.mime_collector_body = None
                # pop the reactor finalized and count the response
                self.pipeline_responses.popleft ()
                self.http_responses += 1
                return self.closing # stall the collector if closing

	# HTTP/1.1 client reactor
        
        http_host = None
        http_version = '1.1'
        http_requests = http_responses = 0

        http_collector_error = handle_close
	http_collector_continue = http_reactor.http_collector_continue

        def http_client_continue (self, request):
                # push one string and maybe a producer in the output fifo ...
                http_request = '%s %s HTTP/%s\r\n' % (
                        request.http_command, 
                        request.http_urlpath, 
                        self.http_version
                        )
                if request.mime_producer_body == None:
                        # GET, HEAD, DELETE, ...
                        #
                        lines = mime_headers.lines (
                                request.mime_producer_headers
                                )
                        lines.insert (0, http_request)
                        self.output_fifo.append (''.join (lines))
                else:
                        # POST and PUT ...
                        #
                        if self.http_version == '1.1':
                                request.mime_producer_body = \
                                        http_reactor.Chunk_producer (
                                                request.mime_producer_body
                                                )
                                request.mime_producer_headers[
                                        'transfer-encoding'
                                        ] = 'chunked'
                        lines = mime_headers.lines (
                                request.mime_producer_headers
                                )
                        lines.insert (0, http_request)
                        self.output_fifo.append (''.join (lines))
                        self.output_fifo.append (
                                request.mime_producer_body
                                )
                # append the reactor to the queue of responses expected ...
                self.pipeline_responses.append (request)
                self.http_requests += 1
                #
                # ready to send.
                

def pipeline (host, port=80, version='1.1'):
        assert (
                type (host) == str and type (port) == int and
                version in ('1.1', '1.0')
                )
        dispatcher = Pipeline ()
        if port == 80:
                dispatcher.http_host = host
        else:
                dispatcher.http_host = '%s:%d' % (host, port)
        dispatcher.http_version = version
        return dispatcher


def connect (host, port=80, version='1.1', timeout=3):
        dispatcher = pipeline (host, port, version)
        tcp_client.connect (dispatcher, (host, port), timeout)
        return dispatcher


# conveniences

class Connections (async_client.Connections):

        def __init__ (
                self, timeout=3, precision=1, 
                resolution=tcp_client.dns_A_resolved
                ):
                async_client.Connections.__init__ (
                        self, timeout, precision, socket.AF_INET
                        )
                resolution (self)

        def __call__ (self, host, port=80, version='1.1'):
                return async_client.Connections.__call__ (
                        self, pipeline (host, port, version), (host, port)
                        )
                        

class Cache (async_client.Cache):

        def __init__ (
                self, timeout=3, precision=1, 
                resolution=tcp_client.dns_A_resolved
                ):
                async_client.Cache.__init__ (
                        self, timeout, precision, socket.AF_INET
                        )
                resolution (self)

	def __call__ (self, host, port=80, version='1.1'):
                """return a cached or a new HTTP pipeline, maybe resolving
                and connecting it first, closing it on connection error or
                if it's socket address cannot be resolved"""
                def Dispatcher ():
                        return pipeline (host, port, version)
                async_client.Cache.__call__ (Dispatcher, (host, port))


class Pool (async_client.Pool):

        def __init__ (
                self, host, port=80, version='1.1',
                size=2, timeout=3, precision=1
                ):
                assert (
                        type (host) == str and type (port) == int and
                        version in ('1.1', '1.0')
                        )
                if port == 80:
                        self.http_host = host
                else:
                        self.http_host = '%s:%d' % (host, port)
                self.http_version = version
                async_client.Pool.__init__ (
                        self, Pipeline, (host, port), 
                        size, timeout, precision, socket.AF_INET
                        )

        def __call__ (self):
                dispatcher = async_client.Pool.__call__ (self)
                dispatcher.http_host = self.http_host
                dispatcher.http_version = self.http_version
                return dispatcher
        

def GET (pipeline, url, headers=None):
        if headers == None:
                headers = {}
        return Request (pipeline, url, headers, 'GET', None)
                
                
def POST (pipeline, url, body, headers=None):
        if headers == None:
                headers = {
                        'Content-Type': 'application/x-www-form-urlencoded'
                        }
        return Request (pipeline, url, headers, 'POST', body)                


#
#