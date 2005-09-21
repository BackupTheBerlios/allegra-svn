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

import time, mimetypes, re, types, os, stat, glob
if os.name == 'nt':
        allegra_time = time.clock
else:
        allegra_time = time.time

from urllib import unquote, quote, unquote_plus, quote_plus

from allegra.loginfo import Loginfo
from allegra.finalization import Finalization
from allegra.producer import Simple_producer, Chunked_producer, File_producer
from allegra.tcp_server import TCP_server_channel, TCP_server
from allegra.mime_collector import MIME_collector, mime_headers_map
from allegra.mime_producer import MIME_producer
from allegra.http_collector import HTTP_collector


class HTTP_server_reactor (MIME_producer, Finalization):

        http_version = '1.1'
        http_response = 404

        def __init__ (self, http_channel):
                self.http_channel = http_channel
                self.http_request_time = allegra_time ()
                assert None == self.http_channel.log (
                        http_channel.mime_collector_lines[0]
                        )
                #assert None == self.http_channel.log (
                #        '\r\n'.join (http_channel.mime_collector_lines), ''
                #        )
                #
                # Reactor instanciated
        
        def http_continue (self, version):
                # complete the HTTP response before it is pushed on the
                # outgoing producer_fifo queue ...
                #
                if self.mime_producer_body == None:
                        # set a response entity if none has been assigned
                        # by previous handler, just dump the response line
                        # and the request headers to the browser.
                        #
                        # TODO: add style remove HTML, it is year 2005 ;-)
                        #
                        self.mime_producer_body = Simple_producer (
                                '<html><body>'
                                '<h1>%d - %s</h1>'
                                '<blockquote><pre>%s</pre></blockquote>'
                                '</body></html>' % (
                                        self.http_response,
                                        self.HTTP_SERVER_RESPONSES[self.http_response],
                                        '\n'.join (self.mime_collector_lines)
                                        )
                                )
                # Close the connection if chunk-encoding is not available
                if self.mime_producer_headers.get (
                        'Transfer-Encoding'
                        ) != 'chunked':
                        self.mime_producer_headers[
                                'Connection'
                                ] = 'close'
                        #
                        # Do not handle HTTP/1.0 keep-alive without Chunks
                        #
                # build the response head
                self.mime_producer_lines = [
                        '%s: %s\r\n' % (n, v)
                        for n,v in self.mime_producer_headers.items ()
                        ]
                self.mime_producer_lines.append ('\r\n')
                self.mime_producer_lines.insert (0, 'HTTP/%s %d %s\r\n' % (
                        version, self.http_response,
                        self.HTTP_SERVER_RESPONSES[self.http_response]
                        ))
                assert None == self.http_channel.log (
                        self.mime_producer_lines[0], ''
                        )
                        
        def finalization (self, reactor):
                # the producer has completed, break possible circular ref,
                # log and time the reactor request/response
                #
                self.http_channel.log (
                        '<react id="%x" secondes="%f"/>' % (
                                id (reactor), 
                                allegra_time () - self.http_request_time
                                ) , ''
                        )
                self.http_channel = None
                #
                # Subclass here to log the response success and other usefull
                # measures when doing HTTP/1.1 workflow. Note that a handler
                # may wrap its own finalization ... making hosted scripts
                # aware of the true success of transmission (and that *is*
                # critical for business applications network :-)
                
        HTTP_SERVER_RESPONSES = {
                #100: "Continue",
                #101: "Switching Protocols",
                200: "OK",
                #201: "Created",
                #202: "Accepted",
                #203: "Non-Authoritative Information",
                #204: "No Content",
                #205: "Reset Content",
                #206: "Partial Content",
                #300: "Multiple Choices",
                #301: "Moved Permanently",
                #302: "Moved Temporarily",
                #303: "See Other",
                #304: "Not Modified",
                #305: "Use Proxy",
                400: "Bad Request",
                #401: "Unauthorized",
                #402: "Payment Required",
                #403: "Forbidden",
                404: "Not Found",
                405: "Method Not Allowed",
                #406: "Not Acceptable",
                #407: "Proxy Authentication Required",
                #408: "Request Time-out",
                #409: "Conflict",
                #410: "Gone",
                #411: "Length Required",
                #412: "Precondition Failed",
                #413: "Request Entity Too Large",
                #414: "Request-URI Too Large",
                #415: "Unsupported Media Type",
                #500: "Internal Server Error",
                #501: "Not Implemented",
                #502: "Bad Gateway",
                #503: "Service Unavailable",
                #504: "Gateway Time-out",
                #505: "HTTP Version not supported"
                }
                #
                # TODO: trim down to a meaningfull subset for an HTTP peer
                #       of implement more than the three 200, 400 and 404 ...
            

HTTP_URI_RE = re.compile ('(?:([^/]*)//([^/]*))?(/[^?]*)([?][^#]+)?(#.+)?')
#
# split a URL into ('http://hostname', '/path', '?query', '#fragment')

class HTTP_server_channel (
        TCP_server_channel, MIME_collector, HTTP_collector
        ):

        ac_out_buffer_size = 1<<16 # use a larger default output buffer

	# HTTP_server_channel

	http_version = '1.0'

	def __init__ (self, conn, addr):
		TCP_server_channel.__init__ (self, conn, addr)
                MIME_collector.__init__ (self)

        def __repr__ (self):
                return '<http-server-channel id="%x"/>' % id (self)                
                
        # adds support for stalled producers to an asynchat channel.

        def writable (self):
                return not (
                        (self.ac_out_buffer == '') and
                        (
                                self.producer_fifo.is_empty () or
                                self.producer_fifo.first ().producer_stalled ()
                                ) and
                        self.connected
                        )

        # Support for stalled producers is a requirement for programming
        # asynchronous peer. It is also a practical solution for simple 
        # asynchronous pipelining of threaded requests. For instance it
        # may be used to thread an HTTP/1.1 requests and push a stalled
        # producer back to the browser that will "produce" as the request
        # progresses, as it thunks data to produce via the select_trigger.

        collect_incoming_data = MIME_collector.collect_incoming_data
        found_terminator = MIME_collector.found_terminator

	def mime_collector_continue (self):
                # handle the HTTP request head
                #
                # "as per the suggestion of http-1.1 section 4.1, (and
                #  Eric Parker <eparker@zyvex.com>), ignore a leading blank
                #  lines (buggy browsers tack it onto the end of POST
                #  requests)" - Sam Rushing
                #
		while self.mime_collector_lines and not self.mime_collector_lines[0]:
			self.mime_collector_lines.pop (0)
                if not self.mime_collector_lines:
                        return 0

                # instanciate a reactor (a collector/producer/finalization)
                # that will hold all states for the HTTP request and response.
                #
		reactor = HTTP_server_reactor (self)
                try:
                        # split the request
			reactor.http_request = (
				method, uri, version
				) = self.mime_collector_lines[0].split ()
		except:
                        # or drop as invalid. the MIME collector is finalized
                        # and the connection will be closed.
                        reactor.mime_producer_headers = {'Connection': 'close'}
			reactor.http_request = self.mime_collector_lines[0]
                        reactor.http_response = 400
                        self.mime_collector_finalize (reactor)
                        return 0 # 400 - invalid

                # Collect the URI parts if any ...
                m = HTTP_URI_RE.match (reactor.http_request[1])
                if m:
                        reactor.http_uri = m.groups ()
                else:
                        reactor.http_uri = (
                                '', reactor.http_request[1], '', ''
                                )
                # parse the collected headers, prepares the producer headers
		self.mime_collector_lines.pop (0)
                reactor.mime_collector_lines = self.mime_collector_lines
		reactor.mime_collector_headers = \
                        self.mime_collector_headers = \
			        mime_headers_map (self.mime_collector_lines)
                reactor.mime_producer_headers = {} # ? ...
		if self.http_version != version[-3:]:
                        # upgrade to 1.1 if possible
			self.http_version = version[-3:]
                        if self.http_version == '1.1':
                                self.mime_collector_finalize = \
                                        self.http_server_response_11
                # pass to the server's handlers, expect one of them to
                # complete the reactor's mime producer headers and body.
                self.http_continue (reactor)
                if method.upper () in ('POST', 'PUT'):
                        if self.mime_collector_body == None:
                                # close the connection for reason of
                                # unimplemented method (do not waiste
                                # bandwith on bogus file uploads).
                                #
                                reactor.mime_producer_headers[
                                        'Connection'
                                        ] = 'close'
                                reactor.http_response = 405
                        else:
                                # wraps the POST or PUT body collector with
                                # the appropriate decoding collectors
                                #
                                return self.http_collector_continue (reactor)
                        
                # or finalize method's response now
		self.mime_collector_finalize (reactor)
		return 0

	def http_server_response_11 (self, reactor):
                if (
			reactor.mime_producer_body and
                        reactor.mime_collector_headers.get (
                                'connection'
                                ) == 'keep-alive'
			):
                        reactor.mime_producer_headers[
                                'Transfer-Encoding'
                                ] = 'chunked'
			reactor.mime_producer_body = Chunked_producer (
				reactor.mime_producer_body
				)
                reactor.http_continue (self.http_version)
                self.push_with_producer (reactor)
                if reactor.mime_producer_headers.get ('Connection') == 'close':
                        self.close_when_done ()

	def http_server_response_10 (self, reactor):
                reactor.http_continue (self.http_version)
                self.push_with_producer (reactor)
		if reactor.mime_collector_headers.get ('connection') != 'keep-alive':
			self.close_when_done ()

	mime_collector_finalize = http_server_response_10


class HTTP_server (TCP_server):

        tcp_server_clients_limit = 16
        tcp_server_precision = 0

        TCP_SERVER_CHANNEL = HTTP_server_channel

        def __init__ (self, handlers, ip, port):
                self.http_handlers = handlers
                TCP_server.__init__ (self, (ip, port))

        def __repr__ (self):
                return '<http-server/>'

        def tcp_server_accept (self, conn, addr):
                channel = TCP_server.tcp_server_accept (self, conn, addr)
                if channel:
                        channel.http_continue = self.http_continue
                return channel

        def tcp_server_close (self, channel):
                del channel.http_continue
                TCP_server.tcp_server_close (self, channel)

        def http_continue (self, reactor):
                for handler in self.http_handlers:
                        if handler.http_match (reactor):
                                try:
                                        return handler.http_continue (reactor)
                                        
                                except:
                                        self.loginfo_traceback ()
                                        reactor.http_response = 500
                                        # 500 - Server Error
                return False


class HTTP_root (Loginfo):
        
        def __init__ (self, path, host=None):
                self.http_path = path
                self.http_host = host or os.path.basename (
                        path
                        ).replace ('-', ':')
                assert None == self.log ('<loaded/>', '')
                
        def __repr__ (self):
                return '<http-root path="%s" host="%s"/>' % (
                        self.http_path, self.http_host
                        )
                
        def http_match (self, reactor, default='index.html'):
                uri = unquote (reactor.http_uri[2])
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


class HTTP_handler (Loginfo):

	def __init__ (self, root):
                paths = [r.replace ('\\', '/') for r in glob.glob (root+'/*')]
                self.http_handler_roots = dict ([
                        (
                                os.path.split (r)[1].replace ('-', ':'), 
                                HTTP_root (r)
                                )
                        for r in paths
                        ])
                print self.http_handler_roots
                        
        def __repr__ (self):
                return '<http-handler/>'
                
	def http_match (self, reactor):
                self.log (reactor.mime_collector_headers.get ('host'))
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
                        reactor.mime_producer_body = File_producer (
                                open (reactor.http_handler_filename, 'rb')
                                ) # TODO: implement gzip, deflate, ...
                else:
                        reactor.http_response = 405
                        return
                        
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
        sys.stderr.write (
                'Allegra HTTP/1.1 Server - Copyleft GPL 2.0\n\n'
                )
        from allegra import async_loop
        root, ip, port = ('./http', '127.0.0.1', 80)
        if len (sys.argv) > 1:
                root = sys.argv[1]
	HTTP_server ([HTTP_handler (root)], ip, port)
        try:
                async_loop.loop ()
        except:
                async_loop.loginfo.loginfo_traceback ()


# A Simple HTTP/1.1 Server that handles only GET requests for static files,
# but which supports virtual hosting nevertheless. It is designed for a peer
# on an offline system or a private network firewalling to the outer edges
# of the network not for a server listening on a public Internet address.
#
# The purpose of thes static HTTP_handler is to provide a test case for the
# simplest HTTP/1.1 GET request with Firefox. It provides Allegra's PRESTo
# with a static web server and a base from which to derive an asynchronous
# REST components web host (see presto_http.py).
#
#
