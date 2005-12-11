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

import types, time, os, stat, glob, mimetypes, urllib, re

from allegra import \
        loginfo, async_chat, producer, tcp_server, \
        mime_headers, mime_reactor, http_reactor
        

if os.name == 'nt':
        allegra_time = time.clock
else:
        allegra_time = time.time


class HTTP_server_reactor (mime_reactor.MIME_producer, loginfo.Loginfo):
        
        mime_collector_body = None
        
        def __repr__ (self):
                return 'http-server-reactor id="%x"' % id (self)
        

# split a URL into ('http://hostname', '/path', '?query', '#fragment')
#
HTTP_URI_RE = re.compile ('(?:([^/]*)//([^/]*))?(/[^?]*)([?][^#]+)?(#.+)?')

class HTTP_server_channel (
        async_chat.Async_chat, mime_reactor.MIME_collector
        ):

        ac_in_buffer_size = 4096 # 4KB input buffer
        ac_out_buffer_size = 1<<16 # 64KB output buffer

	# HTTP_server_channel

	http_version = '1.0'

	def __init__ (self, conn):
		async_chat.Async_chat.__init__ (self, conn)
                self.set_terminator ('\r\n\r\n')

        def __repr__ (self):
                return 'http-server-channel id="%x"' % id (self)                
                
        # adds support for stalled producers to an async_chat channel.

        writable = async_chat.Async_chat.writable_for_stalled

        # Support for stalled producers is a requirement for programming
        # asynchronous peer. It is also a practical solution for simple 
        # asynchronous pipelining of threaded requests. For instance it
        # may be used to thread an HTTP/1.1 requests and push a stalled
        # producer back to the browser that will "produce" as the request
        # progresses, as it thunks data to produce via the select_trigger.

        collect_incoming_data = \
                mime_reactor.MIME_collector.collect_incoming_data
        found_terminator = \
                mime_reactor.MIME_collector.found_terminator

	def mime_collector_continue (self):
                #
                # 1. Grok The Request
                #
		while (
                        self.mime_collector_lines and not 
                        self.mime_collector_lines[0]
                        ):
			self.mime_collector_lines.pop (0)
                if not self.mime_collector_lines:
                        return
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
		reactor = HTTP_server_reactor ()
                reactor.log (self.mime_collector_lines[0], 'request')
                reactor.http_channel = self
                reactor.http_request_time = allegra_time ()
                try:
                        # split the request
			(
				method, uri, version
				) = self.mime_collector_lines[0].split ()
		except:
                        # or drop as invalid. the MIME collector is finalized
                        # and the connection will be closed.
                        reactor.mime_producer_headers = {
                                'Connection': 'close'
                                }
			reactor.http_request = self.mime_collector_lines[0]
                        reactor.http_response = 400
                        self.mime_collector_finalize (reactor)
                        return
                        #
                        # 400 - invalid

                method = method.upper ()
                reactor.http_request = (method, uri, version)
                reactor.http_response = None
                # Split the URI parts if any ...
                m = HTTP_URI_RE.match (uri)
                if m:
                        reactor.http_uri = m.groups ()
                else:
                        reactor.http_uri = (
                                '', reactor.http_request[1], '', ''
                                )
                # parse the collected headers
		self.mime_collector_lines.pop (0)
                reactor.mime_collector_lines = self.mime_collector_lines
		reactor.mime_collector_headers = \
                        self.mime_collector_headers = \
			        mime_headers.map (self.mime_collector_lines)
                # prepares the producer headers and set the channel's version
                # of the HTTP protocol declared by the client (1.0 or 1.1)
                reactor.mime_producer_headers = {} # TODO: complete?
		if self.http_version != version[-3:]:
			self.http_version = version[-3:]
                #
                # 2. Handle The Request
                #
                # pass to the server's handlers, expect one of them to
                # complete the reactor's mime producer headers and body.
                #
                self.http_continue (reactor) # *The* HTTP continuation
                #
                # 3. Continue The Request 
                #
                if method in ('GET', 'HEAD', 'DELETE'):
                        # finalize responses without a MIME body
                        self.mime_collector_finalize (reactor)
                        return

                # finalize POST and PUT when their body is collected, or
                # close the connection for reason of unimplemented 
                # method (do not waiste bandwith on bogus file uploads).
                #
                if reactor.mime_collector_body == None:
                        reactor.mime_producer_headers[
                                'Connection'
                                ] = 'close'
                        reactor.http_response = 501
                        self.mime_collector_finalize (reactor)
                        return
                        #
                        # 501 Not Implemented
                        
                # wraps the POST or PUT body collector with the appropriate 
                # decoding collectors, and continue ...
                #
                self.http_collector_continue (
                        reactor.mime_collector_body
                        )
                # return True
                        
        http_collector_continue = http_reactor.http_collector_continue

        def mime_collector_finalize (self, reactor):
                #
                # 0. Push the reactor in the channel's output fifo and
                #    reset the channel's and MIME collector's state
                #
                self.set_terminator ('\r\n\r\n')
                self.mime_collector_headers = \
                        self.mime_collector_lines = \
                        self.mime_collector_body = None
                self.producer_fifo.append (reactor)
                #
                # 1. complete the HTTP response producer 
                #
                if reactor.http_request[0] in (
                        'GET', 'POST'
                        ) and  reactor.mime_producer_body == None:
                        # supply a response entity if one is required for the
                        # request's method and that none has been assigned
                        # by a previous handler
                        reactor.mime_producer_body = producer.Simple_producer (
                                self.HTTP_SERVER_RESPONSE % (
                                        reactor.http_response,
                                        self.HTTP_SERVER_RESPONSES[
                                                reactor.http_response
                                                ],
                                        '\n'.join (
                                                reactor.mime_collector_lines
                                                )
                                        )
                                )
                if (
                        reactor.mime_producer_body != None and
                        self.http_version == '1.1'
                        ):
                        # allways use Chunked Transfer-Encoding for HTTP/1.1
                        reactor.mime_producer_headers[
                                'Transfer-Encoding'
                                ] = 'chunked'
                        reactor.mime_producer_body = \
                                http_reactor.Chunk_producer (
                                        reactor.mime_producer_body
                                        )
                if reactor.mime_producer_headers.get (
                        'Transfer-Encoding'
                        ) != 'chunked':
                        # Do not keep-alive without chunk-encoding
                        reactor.mime_producer_headers[
                                'Connection'
                                ] = 'close'
                # Build the response head with the reactor's MIME headers, 
                # the channel's HTTP version the reactor's HTTP response
                # code.
                #
                reactor.mime_producer_lines = mime_headers.lines (
                        reactor.mime_producer_headers
                        )
                reactor.mime_producer_lines.insert (0, 'HTTP/%s %d %s\r\n' % (
                        self.http_version, reactor.http_response,
                        self.HTTP_SERVER_RESPONSES[reactor.http_response]
                        ))
                #
                # 2. initiate send decide wether or not to close when done
                #
                self.handle_write ()
                if reactor.mime_collector_headers.get (
                        'connection'
                        ) != 'keep-alive':
                        self.close_when_done ()
                # finally log the response's first line
                reactor.log (reactor.mime_producer_lines[0][:-2], 'response')
                #

        HTTP_SERVER_RESPONSE = (
                '<html>'
                '<head><title>Error</title></head>'
                '<body>'
                '<h1>%d %s</h1>'
                '<pre>%s</pre>'
                '</body>'
                '</html>'
                )

        HTTP_SERVER_RESPONSES = {
                100: "Continue",
                101: "Switching Protocols",
                200: "OK",
                201: "Created",
                202: "Accepted",
                203: "Non-Authoritative Information",
                204: "No Content",
                205: "Reset Content",
                206: "Partial Content",
                300: "Multiple Choices",
                301: "Moved Permanently",
                302: "Moved Temporarily",
                303: "See Other",
                304: "Not Modified",
                305: "Use Proxy",
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
            

def http_server_accept (server, channel):
        channel.http_continue = server.http_continue

def http_continue (server, reactor):
        for handler in server.http_handlers:
                if handler.http_match (reactor):
                        try:
                                return handler.http_continue (reactor)
                                
                        except:
                                ctb = server.loginfo_traceback ()
                                reactor.http_response = 500
                                return False
                                #
                                # 500 - Server Error
                                
        reactor.http_response = 404
        return False
        #
        # 404 - Not Found

def http_server_close (server, channel):
        del channel.http_continue


class HTTP_server (tcp_server.TCP_server_limit):

        TCP_SERVER_CHANNEL = HTTP_server_channel

        def __init__ (self, handlers, ip, port=80):
                self.http_handlers = handlers
                tcp_server.TCP_server_limit.__init__ (self, (ip, port))

        def __repr__ (self):
                return 'http-peer id="%x"' % id (self)

        tcp_server_accept = http_server_accept

        tcp_server_close = http_server_close

        http_continue = http_continue
        

class HTTP_root (loginfo.Loginfo):
        
        def __init__ (self, path, host=None):
                self.http_path = path
                self.http_host = host or os.path.basename (
                        path
                        ).replace ('-', ':')
                assert None == self.log (
                        'loaded path="%s"' % path, 'debug'
                        )
                
        def __repr__ (self):
                return 'http-root host="%s"' % self.http_host
                
        def http_match (self, reactor, default='index.html'):
                uri = urllib.unquote (reactor.http_uri[2])
                if uri[-1] == '/':
                        uri += default
                reactor.http_handler_filename = self.http_path + uri
                try:
                        reactor.http_handler_stat = os.stat (
                                reactor.http_handler_filename
                                )
                except OSError:
                        # the handler is "transparent", if the file does not
                        # exists another handler may be used ...
                        return False
                        
                return stat.S_ISREG (reactor.http_handler_stat[0])


class HTTP_handler (loginfo.Loginfo):

	def __init__ (self, root):
                paths = [r.replace ('\\', '/') for r in glob.glob (root+'/*')]
                self.http_handler_roots = dict ([
                        (
                                os.path.split (r)[1].replace ('-', ':'), 
                                HTTP_root (r)
                                )
                        for r in paths
                        ])
                        
        def __repr__ (self):
                return 'http-handler'
                
	def http_match (self, reactor):
                http_root = self.http_handler_roots.get (
                        reactor.mime_collector_headers.get ('host')
                        )
                if http_root == None:
                        return False
                        
                return http_root.http_match (reactor)

	def http_continue (self, reactor):
                # TODO: use asynchronous channel for file I/O instead and
                #       implement stalled producers in the channel. also,
                #       handle HEAD method and reply correctly for unhandled
                #       methods ...
                #
                if reactor.http_request[0].upper () == 'GET':
                        reactor.mime_producer_body = producer.File_producer (
                                open (reactor.http_handler_filename, 'rb')
                                ) # TODO: implement gzip, deflate, ...
                else:
                        reactor.http_response = 405
                        return
                        #
                        # 405 Method Not Allowed
                        
                reactor.mime_producer_headers[
                        'Last-Modified'
                        ] = time.asctime (
                                time.gmtime (reactor.http_handler_stat[7])
                                ) + (' %d' % time.timezone)
                content_type, content_encoding = mimetypes.guess_type (
                        reactor.http_handler_filename
                        )
	        reactor.mime_producer_headers[
                        'Content-Type'
                        ] = content_type or 'text/html'
                if content_encoding:
                        reactor.mime_producer_headers[
                                'Content-Encoding'
                                ] = content_encoding
                reactor.http_response = 200
                #
                # TODO: add last-modified, cache, charset, etc ...


if __name__ == '__main__':
        import sys
        from allegra import loginfo, async_loop
        loginfo.log (
                'Allegra HTTP/1.1 Server'
                ' - Coyright 2005 Laurent A.V. Szyster | Copyleft GPL 2.0',
                'info'
                )
        root, ip, port = ('./http', '127.0.0.1', 80)
        if len (sys.argv) > 1:
                root = sys.argv[1]
	HTTP_server ([HTTP_handler (root)], ip, port)
        async_loop.loop ()
        
        
# Note about this implementation
#
# This HTTP/1.1 server supports non-blocking handlers, like the one
# provided to cache and serve static files from a synchronous filesystem.
# It is a fully-featured HTTP server, with support for GET and POST
# methods, chunked transfer encoding, pipelining for HTTP/1.1 and 1.0
# alike. It is integrated with Allegra TCP server models (local and
# unlimited, private and managed, public and throttled) and provides
# a practical interface and implementation to derive other services
# than static filesystems, like BSDDB databases and PNS metabases.
#
# Most remarkably, this interface is the basis for PRESTo, Allegra's 
# web peer, which serves REST methods of component instances loaded
# from any of the above three type of information storage system.
#
# The fact is that this is not *just* a static file server, it acts
# more like a filesystem cache, globbing in memory the web as it is
# served, then throwing it as fast as possible. It's a busy-body static
# web cache that you can tune by adjusting the parameters for the
# garbage gollector of the CPython VM.
#
# Note finally that each server is expected to have only one handler
# implementation, which may delegate a request but must do so explicitely.
# The rational is that this is not a library to develop an extensible 
# Apache-like server. This module is designed to either develop a special
# purpose web server or a peer for component instances, where functions
# are not layered as handlers but integrated in a class definition.
# 