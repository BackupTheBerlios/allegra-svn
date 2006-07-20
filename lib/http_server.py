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

import types, weakref, time, os, socket, stat, glob, mimetypes, urllib, re

from allegra import (
        netstring, loginfo, async_loop, finalization, 
        async_chat, producer, async_server,
        mime_headers, mime_reactor, http_reactor
        )

HTTP_RESPONSE = (
        '<html><head><title>Error</title></head>'
        '<body><h1>%d %s</h1><pre>%s</pre></body></html>'
        )

HTTP_RESPONSES = {
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
        

if os.name == 'nt':
        allegra_time = time.clock
        _LISTEN_MAX = 5
else:
        allegra_time = time.time
        _LISTEN_MAX = 1024


class Reactor (mime_reactor.MIME_producer, loginfo.Loginfo):
        
        mime_collector_body = None
        
        http_response = http_handler = None
        
        def __repr__ (self):
                return 'http-server-reactor id="%x"' % id (self)
        
        def http_continuation (self): pass
        

# split a URL into ('protocol:', 'hostname', '/path', 'query', '#fragment')
#
HTTP_URI_RE = re.compile ('(?:([^/]*)//([^/]*))?(/[^?]*)[?]?([^#]+)?(#.+)?')

class Dispatcher (
        mime_reactor.MIME_collector, async_chat.Dispatcher
        ):

        ac_in_buffer_size = 4096 # 4KB input buffer
        ac_out_buffer_size = 1<<14 # 16KB output buffer

	http_version = '1.0'

	def __init__ (self):
		async_chat.Dispatcher.__init__ (self)
                self.set_terminator ('\r\n\r\n')

        def __repr__ (self):
                return 'http-server-channel id="%x"' % id (self)                
                
	def mime_collector_continue (self):
		while (
                        self.mime_collector_lines and not 
                        self.mime_collector_lines[0]
                        ):
			self.mime_collector_lines.pop (0)
                if not self.mime_collector_lines:
                        return self.closing
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
                assert None == reactor.log (
                        self.mime_collector_lines[0], 'request'
                        )
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
			reactor.http_request = self.mime_collector_lines[0]
                        reactor.mime_collector_headers = {}
                        reactor.mime_producer_headers = {
                                'Connection': 'close'
                                }
                        reactor.http_response = 400
                        self.http_reactor = reactor
                        self.mime_collector_finalize ()
                        return self.closing
                        #
                        # 400 - invalid

                method = method.upper ()
                reactor.http_request = (method, uri, version)
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
                # push the (stalled) reactor in the channel's output fifo
                self.output_fifo.append (reactor)
                # pass to the server's handlers, expect one of them to
                # complete the reactor's mime producer headers and body.
                if self.async_server.http_continue (reactor):
                        if reactor.http_request[0] in ('POST', 'PUT'):
                                return True
                                #
                                # it is up to the reactor's handler to 
                                # finalize the HTTP response ...

                        return self.closing
                
                return self.http_continue (reactor)
                
        def http_continue (self, reactor):
                #if reactor.http_response == None:
                #        # do not continue yet if a response is not set
                #        return False
                #
                if reactor.http_request[0] in ('GET', 'HEAD', 'DELETE'):
                        # finalize requests without a MIME body now!
                        return self.mime_collector_finalize (reactor)

                # finalize POST and PUT when their body is collected, or
                # close the connection for reason of unimplemented 
                # method (do not waiste bandwith on bogus file uploads).
                #
                if reactor.mime_collector_body == None:
                        reactor.mime_producer_headers[
                                'Connection'
                                ] = 'close'
                        reactor.http_response = 501
                        return self.mime_collector_finalize (reactor)
                        #
                        # 501 Not Implemented
                        
                # wraps the POST or PUT body collector with the appropriate 
                # decoding collectors, and continue ...
                #
                self.http_reactor = reactor
                return self.http_collector_continue (
                        reactor.mime_collector_body
                        )
                        
        http_collector_continue = http_reactor.http_collector_continue

        def mime_collector_finalize (self, reactor=None):
                # reset the channel state to collect the next request ...
                self.set_terminator ('\r\n\r\n')
                self.mime_collector_headers = \
                        self.mime_collector_lines = \
                        self.mime_collector_body = None
                if reactor == None:
                        # current request's body collected, continue.
                        reactor = self.http_reactor
                        reactor.http_continuation (reactor)
                        self.http_reactor = None
                # finalize the current request
                if reactor.http_handler != None:
                        reactor.http_handler.http_finalize (reactor)
                # Complete the HTTP response producer
                if reactor.mime_producer_body == None and (
                        reactor.http_request[0] in ('GET', 'POST')
                        ):
                        # supply a response entity if one is required for the
                        # request's method and that none has been assigned
                        # by a previous handler
                        reactor.mime_producer_body = producer.Simple (
                                HTTP_RESPONSE % (
                                        reactor.http_response,
                                        HTTP_RESPONSES[reactor.http_response],
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
                # code. Then initiate send decide wether or not to close 
                # when done ...
                #
                reactor.mime_producer_lines = mime_headers.lines (
                        reactor.mime_producer_headers
                        )
                reactor.mime_producer_lines.insert (
                        0, 
                        'HTTP/%s %d %s\r\n' 
                        'Date: %s\r\n' 
                        'Server: Allegra\r\n' % (
                                self.http_version, reactor.http_response,
                                HTTP_RESPONSES[reactor.http_response],
                                time.strftime (
                                        '%a, %d %b %Y %H:%M:%S GMT', 
                                        time.gmtime (time.time ())
                                        )
                                )
                        )
                if reactor.mime_collector_headers.get (
                        'connection'
                        ) != 'keep-alive':
                        # close when done if not kept alive
                        self.output_fifo.append (None)
                #
                # do not iniate send, wait for a write event instead ...
                #self.handle_write ()
                #
                # ... finally, log the response's first line.
                #assert None == reactor.log (
                #        reactor.mime_producer_lines[0][:-2], 'response'
                #        )
                return self.closing

        # Support for stalled producers is a requirement for programming
        # asynchronous peer. It is also a practical solution for simple 
        # asynchronous pipelining of threaded requests. For instance it
        # may be used to thread an HTTP/1.1 requests and push a stalled
        # producer back to the browser that will "produce" as the request
        # progresses, as it thunks data to produce via the select_trigger.


# A Static Cache Root with Simple Logging

def http_log_line (self, reactor):
        loginfo.log (' '.join ((
                '%s:%d' % reactor.http_channel.addr,
                '(%s %s %s)' % reactor.http_request,
                '%d' % reactor.http_response
                )))

def http_log_netstrings (self, reactor):
        loginfo.log (netstring.netstrings ((
                reactor.http_channel.addr,
                reactor.http_request,
                reactor.http_response
                )))

if __debug__:
        http_log = http_log_line
else:
        http_log = http_log_netstrings
        

def none (): pass

class File_cache (loginfo.Loginfo, finalization.Finalization):

        def __init__ (self, path): #, host):
                self.http_path = path
                # self.http_host = host
                self.http_cached = {}
                assert None == self.log (
                        'loaded path="%s"' % path, 'debug'
                        )
                
        def __repr__ (self):
                return 'http-cache path="%s"' % self.http_path
        
        def http_continue (self, reactor):
                if reactor.http_request[0] != 'GET':
                        reactor.http_response = 405 # Method Not Allowed 
                        return False
                        #
                        # TODO: add support for HEAD
                        
                filename = self.http_path + self.http_urlpath (reactor)
                teed = self.http_cached.get (filename, none) ()
                if teed != None:
                        reactor.mime_producer_headers.update (
                                teed.mime_headers
                                )
                        reactor.mime_producer_body = \
                                producer.Tee (teed)
                        reactor.http_response = 200
                        return False

                try:
                        result = os.stat (filename)
                except:
                        result = None
                if result == None or not stat.S_ISREG (result[0]):
                        reactor.http_response = 404
                        return False
                        
                teed = producer.File (open (filename, 'rb'))
                content_type, content_encoding = \
                        mimetypes.guess_type (filename)
                teed.mime_headers = {
                        'Last-Modified': (
                                time.asctime (time.gmtime (result[7])) + 
                                (' %d' % time.timezone)
                                ),
                        'Content-Type': content_type or 'text/html',
                        }
                if content_encoding:
                        teed.mime_headers['Content-Encoding'] = \
                                content_encoding
                reactor.mime_producer_headers.update (teed.mime_headers)
                reactor.mime_producer_body = producer.Tee (teed)
                reactor.http_response = 200
                self.http_cached[filename] = weakref.ref (teed)
                return False
        
        def http_urlpath (self, reactor):
                return urllib.unquote (reactor.http_uri[2])
        
        http_finalize = http_log


class Listen (async_server.Listen):
        
        http_hosts = {}
        
        def __init__ (
                self, addr, precision=3, max=_LISTEN_MAX, 
                family=socket.AF_INET
                ):
                async_server.Listen.__init__ (
                        self, Dispatcher, addr, precision, max, family 
                        )
                        
        def __repr__ (self):
                return 'http-listen'

        def http_continue (self, reactor):
                handler = self.http_hosts.get (
                        reactor.mime_collector_headers.get ('host')
                        )
                if handler == None:
                        reactor.http_response = 404 # Not Found
                        return False
        
                reactor.http_handler = handler
                return handler.http_continue (reactor)
                

def http_hosts (root, host, port):
        if port == 80:
                if host == None:
                        return [
                                (os.path.split (r)[1], r)
                                for r in [
                                        r.replace ('\\', '/') 
                                        for r in glob.glob (root+'/*')
                                        ]
                                ]
                                
                else:        
                        return ((host, root), )
        
        elif host == None:
                return [
                        ('%s:%d' % (os.path.split (r)[1], port), r)
                        for r in [
                                r.replace ('\\', '/') 
                                for r in glob.glob (root+'/*')
                                ]
                        ]
                        
        else:
                return (('%s:%d' % (host, port), root), )


def cli (argv):
        # TODO: move up to tcp_server.py, this is a usefull interface
        #       for other services than HTTP/1.1 (for instance a netstring
        #       PRESTo peer not having to suffer from CRLF delimited
        #       troubles, MIME headers parsing and HTTP's overhead).
        #
        root, ip, port, host = ('.', '127.0.0.1', 80, None)
        if len (argv) > 1:
                root = argv[1]
                if len (argv) > 2:
                        try:
                                ip, port = argv[2].split (':')
                        except:
                                ip = argv[2]
                        else:
                                port = int (port)
                        if len (argv) > 3:
                                host = argv[3]
        root = os.path.abspath (root)
        return root, ip, port, host


if __name__ == '__main__':
        import sys
        if '-s' in sys.argv:
                sys.argv.remove ('-s')
                from allegra import sync_stdio
        elif not __debug__:
                from allegra import sync_stdio
        else:
                sync_stdio = None
        if '-d' in sys.argv:
                sys.argv.remove ('-d')
                loginfo.Loginfo_stdio.log = \
                        loginfo.Loginfo_stdio.loginfo_netlines
        loginfo.log (
                'Allegra HTTP/1.1 Server'
                ' - Coyright 2005 Laurent A.V. Szyster | Copyleft GPL 2.0',
                'info'
                )
        root, ip, port, host = cli (sys.argv)
        #
        listen = Listen ((ip, port))
        listen.http_hosts = dict ([
                (h, File_cache (p)) 
                for h, p in http_hosts (root, host, port)
                if stat.S_ISDIR (os.stat (p)[0])
                ])
        if not ip.startswith ('127.'):
                listen.server_resolved = (lambda addr: addr[0])
                if ip.startswith ('192.168.') or ip.startswith ('10.') :
                        async_server.accept_named (listen, 256)
                else:
                        async_server.accept_named (listen, 2)
                async_server.inactive (listen, 3)
        async_loop.catch (listen.server_shutdown)
        if sync_stdio:
                sync_stdio.Sync_stdoe ().start ()
        del listen
        async_loop.dispatch ()
        assert None == finalization.collect ()