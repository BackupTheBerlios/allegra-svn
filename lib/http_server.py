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

"Asynchronous HTTP Server"

import re
from time import time, strftime, gmtime

from allegra import (
        netstring, loginfo, async_loop, finalization, async_chat, producer,
        mime_headers, mime_reactor, http_reactor
        )

HTTP_RESPONSES = {
        100: "Continue",
        101: "Switching Protocols",
        200: "OK", # GET and/or POST ...
        201: "Created",
        202: "Accepted",
        203: "Non-Authoritative Information",
        204: "No Content",
        205: "Reset Content",
        206: "Partial Content",
        300: "Multiple Choices",
        301: "Moved Permanently",
        302: "Moved Temporarily", # ... continue ...
        303: "See Other",
        304: "Not Modified",
        305: "Use Proxy", # ... that's all folks, use your cache.
        400: "Bad Request",
        401: "Unauthorized",
        402: "Payment Required",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        406: "Not Acceptable",
        407: "Proxy Authentication Required",
        408: "Request Time-out",
        409: "Conflict",
        410: "Gone",
        411: "Length Required",
        412: "Precondition Failed",
        413: "Request Entity Too Large",
        414: "Request-URI Too Large",
        415: "Unsupported Media Type",
        500: "Internal Server Error", 
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Time-out",
        505: "HTTP Version not supported"
        }
        
HTTP_RESPONSE = (
        '<html><head><title>Error</title></head>'
        '<body><h1>%s %d %s</h1><pre>%s\n%s</pre></body></html>'
        )

class Reactor (mime_reactor.MIME_producer, loginfo.Loginfo):
        
        collector_lines = ()
        collector_body = None
        http_request = ('?', '?', 'HTTP/0.9')
        
        def __repr__ (self):
                return 'presto id="%x"' % id (self)
        
        def http_produce (self, response, headers=(), body=None):
                self.http_response = response
                # Complete the HTTP response producer
                self.producer_headers.update (headers)
                if body == None and (
                        self.http_request[0] in ('GET', 'POST')
                        ):
                        # supply a response entity if one is required for the
                        # request's method and that none has been assigned
                        # by a previous handler
                        self.producer_body = producer.Simple (
                                HTTP_RESPONSE % (
                                        self.http_request[2], 
                                        response,
                                        HTTP_RESPONSES[response],
                                        ' '.join (self.http_request),
                                        '\n'.join (self.collector_lines)
                                        )
                                )
                else:
                        self.producer_body = body
                if self.http_request[2] == 'HTTP/1.1':
                        # allways use Chunked Transfer-Encoding for HTTP/1.1
                        if self.producer_body != None:
                                self.producer_headers[
                                        'Transfer-Encoding'
                                        ] = 'chunked'
                                self.producer_body = \
                                        http_reactor.Chunk_producer (
                                                self.producer_body
                                                )
                else:
                        # Do not keep-alive without chunk-encoding
                        self.producer_headers['Connection'] = 'close'
                # Build the response head with the reactor's MIME headers, 
                # the channel's HTTP version the reactor's HTTP response
                # code. Then initiate send decide wether or not to close 
                # when done ...
                #
                self.producer_lines = mime_headers.lines (
                        self.producer_headers
                        )
                self.producer_lines.insert (
                        0, 
                        '%s %d %s\r\n' 
                        'Date: %s\r\n' 
                        'Server: Allegra\r\n' % (
                                self.http_request[2], 
                                response,
                                HTTP_RESPONSES[response],
                                strftime (
                                        '%a, %d %b %Y %H:%M:%S GMT', 
                                        gmtime (time ())
                                        )
                                )
                        )
        
        # Support for stalled producers is a requirement for programming
        # asynchronous peer. It is also a practical solution for simple 
        # asynchronous pipelining of threaded requests. For instance it
        # may be used to thread an HTTP/1.1 requests and push a stalled
        # producer back to the browser that will "produce" as the request
        # progresses, as it thunks data to produce via the select_trigger.
                
# split a URL into ('protocol:', 'hostname', '/path', 'query', '#fragment')
#
HTTP_URI_RE = re.compile ('(?:([^/]*)//([^/]*))?(/[^?]*)[?]?([^#]+)?(#.+)?')

class Dispatcher (
        mime_reactor.MIME_collector, async_chat.Dispatcher
        ):

        ac_in_buffer_size = 4096 # 4KB input buffer
        ac_out_buffer_size = 1<<14 # 16KB output buffer

	def __init__ (self):
		async_chat.Dispatcher.__init__ (self)
                self.set_terminator ('\r\n\r\n')

        def __repr__ (self):
                return 'http-server-channel id="%x"' % id (self)                
        
	def collector_continue (self):
		while (
                        self.collector_lines and not 
                        self.collector_lines[0]
                        ):
			self.collector_lines.pop (0)
                if not self.collector_lines:
                        return False
                        #
                        # From Medusa's http_server.py Original Comment:
                        #
                        # "as per the suggestion of http-1.1 section 4.1, (and
                        #  Eric Parker <eparker@zyvex.com>), ignore a leading
                        #  blank lines (buggy browsers tack it onto the end of
                        #  POST requests)" - Sam Rushing

                # instanciate a reactor that will hold all states for the 
                # HTTP request and response.
                #
		reactor = Reactor ()
                # push the stalled reactor in the channel's output fifo
                self.output_fifo.append (reactor)
                reactor.producer_headers = {}
                reactor.dispatcher = self
                try:
                        # split the request in: command, uri and version
			(
				method, url, version
				) = self.collector_lines[0].split ()
		except:
                        reactor.http_response (400, ((
                                'Connection', 'close'
                                ),))
                        return True # stall the collector!

                reactor.http_request = (method.upper (), url, version)
                # save and parse the collected headers
                self.collector_lines.pop (0)
                reactor.collector_lines = self.collector_lines
                reactor.collector_headers = mime_headers.map (
                        self.collector_lines
                        )
                self.collector_lines = None
                # Split the URI parts if any ...
                m = HTTP_URI_RE.match (url)
                if m:
                        reactor.http_uri = m.groups ()
                else:
                        reactor.http_uri = ('', '', url, '', '')
                # pass to the server's handlers, expect one of them to
                # complete the reactor's mime producer headers and body.
                if self.async_server.http_continue (reactor):
                        return True
                        #
                        # A GET controller could very well ask to stall the
                        # HTTP connection's collector (ie: to defer the
                        # response to the current request and all the ones 
                        # pipelined there-after).
                
                return self.http_continue (reactor)
                
        def http_continue (self, reactor):
                if reactor.collector_body == None:
                        if not (reactor.http_request[0] in (
                                'GET', 'HEAD', 'DELETE'
                                )):
                                reactor.http_response (500, ((
                                        'Connection', 'close'
                                        ),))
                                return True
                        
                else:
                        self.http_collector_continue (reactor.collector_body)
                return self.closing
                        
        http_collector_continue = http_reactor.http_collector_continue
        
        def collector_finalize (self):
                # reset the channel state to collect the next request,
                self.collector_body = None
                self.set_terminator ('\r\n\r\n')
                # current request's body collected, maybe continue ...
                if self.async_server.http_continue (self.output_fifo[-1]):
                        return True
                
                return self.closing # ... or stall if closing

        def handle_close (self):
                "close the dispatcher and maybe terminate the collector"
                self.close ()
                if self.collector_body:
                        body = self.collector_body
                        depth = self.collector_depth
                        while depth and not body.found_terminator (): 
                                depth -= 1
                        if depth < 1:
                                self.log (
                                        '%d' % self.collector_depth,
                                        'collector-leak'
                                        )
