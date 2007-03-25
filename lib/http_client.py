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

"http://laurentszyster.be/blog/http_client/"

import socket

from allegra import (
	loginfo, finalization,
        async_chat, producer, collector, async_client,
        tcp_client, mime_headers, mime_reactor, http_reactor
        )


class Reactor (finalization.Finalization):
                
        http_response = collector_headers = collector_body = None
        
        def __init__ (
                self, method, pipeline, url, headers, produce=None
                ):
                headers ['Host'] = pipeline.http_host
                self.http_pipeline = pipeline
                self.http_urlpath = url
                self.http_method = method
                self.producer_headers = headers
                self.producer_body = produce

        def __call__ (self, collect=None):
                self.collector_body = collect
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

        pipeline_keep_alive = True

        def __init__ (self):
                async_chat.Dispatcher.__init__ (self)
                self.set_terminator ('\r\n\r\n')
                self.pipeline_set ()
                
        def __repr__ (self):
                return 'http-client-pipeline id="%x"' % id (self)

        __call__ = Pipeline.pipeline # pipeline(request) -> request
                
	# async_chat
        
	def handle_connect (self):
                "fill the pipeline's output_fifo if there are new requests"
                if self.pipeline_requests:
			self.pipeline_wake_up ()

        def handle_close (self):
                "assert debug log of the pipeline queues states and counters"
                assert None == self.log ('{'
                        ' "requests": %d, "responses": %d,'
                        ' "pending": %d, "failed": %d'
                        ' }' % (
                                self.http_requests, 
                                self.http_responses,
                                len (self.pipeline_requests),
                                len (self.pipeline_responses)
                                ), 'debug'
                        )
		self.close ()
                
	# pipeline

        def pipeline_wake_up (self):
                if self.http_version == '1.1':
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
			request.producer_headers['connection'] = 'keep-alive'
		else:
			request.producer_headers['connection']= 'close'
		self.http_client_continue (request)

	def pipeline_wake_up_11 (self):
		# HTTP/1.1 pipeline, send all at once and maybe close when
		# done if not keep-aliver.
		#
                request = self.pipeline_requests.popleft ()
		while self.pipeline_requests:
                        # push all request's reactors
			request.producer_headers['connection'] = 'keep-alive'
                        self.http_client_continue (request)
                        request = self.pipeline_requests.popleft ()
		# push the last one
                if self.pipeline_keep_alive:
                        request.producer_headers['connection'] = 'keep-alive'
                else:
                        # close when done and not kept alive
                        request.producer_headers['connection']= 'close'
		self.http_client_continue (request)
 		
	# MIME collector

	def collector_continue (self):
                while (
                        self.collector_lines and not 
                        self.collector_lines[0]
                        ):
                        self.collector_lines.pop (0)
                if not self.collector_lines:
                        return self.closing
                        #
                        # make sure that the collector is stalled once the
                        # dispatcher has been closed.
                
		request = self.pipeline_responses[0]
		try:
			(
				http_version, request.http_response
				) = self.collector_lines.pop (
					0
					).split (' ', 1)
		except:
                        assert None == self.log (
                                'invalid response line', 'debug'
                                )
			self.http_collector_error ()
			return True

                self.http_version = http_version[-3:]
		request.collector_headers = \
			self.collector_headers = \
			mime_headers.map (self.collector_lines)
		if (
			request.http_method == 'HEAD' or
			request.http_response[:3] in ('204', '304', '305')
			):
                        self.collector_finalize ()
                else:
		        self.http_collector_continue (
                                request.collector_body
                                )
                return self.closing # stall the collector if closing
		
	def collector_finalize (self):
                # pop the reactor finalized and count the response
                self.pipeline_responses.popleft ()
                self.http_responses += 1
                if self.closing:
                        return True # stall the collector if closing
                
                # wake up the pipeline if there are request pipelined
                # and that the connection is kept alive
                if (self.pipeline_requests and (
                        self.http_version == '1.1' or 
                        self.collector_headers.get (
                                'connection'
                                ) == 'keep-alive'
                        )):
                        self.pipeline_wake_up ()
                # reset the channel state to collect the next request ...
                self.set_terminator ('\r\n\r\n')
                self.collector_headers = \
                        self.collector_lines = self.collector_body = None
                return False

	# HTTP/1.1 client reactor
        
        http_host = None
        http_version = '1.1'
        http_requests = http_responses = 0

        http_collector_error = handle_close
	http_collector_continue = http_reactor.http_collector_continue

        def http_client_continue (self, request):
                # push one string and maybe a producer in the output fifo ...
                http_request = '%s %s HTTP/%s\r\n' % (
                        request.http_method, 
                        request.http_urlpath, 
                        self.http_version
                        )
                if request.producer_body == None: # GET, HEAD and DELETE
                        lines = mime_headers.lines (request.producer_headers)
                        lines.insert (0, http_request)
                        self.output_fifo.append (''.join (lines))
                else: # POST and PUT
                        if self.http_version == '1.1':
                                request.producer_body = \
                                        http_reactor.Chunk_producer (
                                                request.producer_body
                                                )
                                request.producer_headers[
                                        'transfer-encoding'
                                        ] = 'chunked'
                        lines = mime_headers.lines (request.producer_headers)
                        lines.insert (0, http_request)
                        self.output_fifo.append (''.join (lines))
                        self.output_fifo.append (request.producer_body)
                # append the reactor to the queue of responses expected ...
                self.pipeline_responses.append (request)
                self.http_requests += 1
                #
                # ready to send.
                

def pipeline (host, port, version):
        dispatcher = Pipeline ()
        if port == 80:
                dispatcher.http_host = host
        else:
                dispatcher.http_host = '%s:%d' % (host, port)
        dispatcher.http_version = version
        return dispatcher

def connect (host, port=80, version='1.1', timeout=3.0):
        dispatcher = pipeline (host, port, version)
        tcp_client.connect (dispatcher, (host, port), timeout)
        return dispatcher


# conveniences

def decorated (host, port, version):
        def Dispatcher ():
                dispatcher = Pipeline ()
                if port == 80:
                        dispatcher.http_host = host
                else:
                        dispatcher.http_host = '%s:%d' % (host, port)
                dispatcher.http_version = version
                return dispatcher
        return Dispatcher

def Connections (timeout=3.0, precision=1.0):
        connections = tcp_client.Connections (timeout, precision)
        def call (host, port=80, version='1.1'):
                return connections (
                        decorated (host, port, version)(), (host, port)
                        )
                        
        return call

def Cache (timeout=3.0, precision=1.0):
        cache = tcp_client.Cache (timeout, precision)
        def call (host, port=80, version='1.1'):
                return cache (
                        decorated (host, port, version), (host, port)
                        )
                
        return call

def Pool (host, port=80, version='1.1', size=2, timeout=3.0, precision=1.0):
        assert (
                type (host) == str and type (port) == int and
                version in ('1.1', '1.0')
                )
        return tcp_client.Pool (
                decorated (host, port, version), 
                (host, port), size, timeout, precision
                )

if __name__ == '__main__':
        #
        # TODO: 
        #
        # implement Apache's ab interface subset, starting with:
        #
        #   -n -c "http://host/path?query" < POST.DATA
        #
        # and quickly move up to the real thing, with Cookies and basic
        # authorization. 
        
        pass