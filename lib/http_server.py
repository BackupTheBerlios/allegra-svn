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

import types, weakref, time, os, stat, glob, mimetypes, urllib, re

from allegra import \
        netstring, loginfo, async_loop, finalization, synchronizer, \
        async_chat, producer, tcp_server, \
        mime_headers, mime_reactor, http_reactor
        

if os.name == 'nt':
        allegra_time = time.clock
else:
        allegra_time = time.time


class HTTP_server_reactor (mime_reactor.MIME_producer, loginfo.Loginfo):
        
        mime_collector_body = None
        
        http_handler = http_response = None
        
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

	http_version = '1.0'

	def __init__ (self, conn):
		async_chat.Async_chat.__init__ (self, conn)
                self.set_terminator ('\r\n\r\n')

        def __repr__ (self):
                return 'http-server-channel id="%x"' % id (self)                
                
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
                        return False
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
                # push the (stalled) reactor in the channel's output fifo
                self.producer_fifo.append (reactor)
                # pass to the server's handlers, expect one of them to
                # complete the reactor's mime producer headers and body.
                if self.http_server.http_continue (reactor):
                        return reactor.http_request[0] in ('POST', 'PUT')
                        #
                        # it is up to the reactor's handler to properly
                        # finalize the HTTP response, here one of the the
                        # server's virtual hosts instance.
                        #
                        # return False and stall the collector we expect a
                        # MIME body collector to be provided ...
                
                return self.http_continue (reactor)
                
        def http_continue (self, reactor):
                if reactor.http_response == None:
                        # do not continue yet if a response is not set
                        return False
                
                self.http_reactor = reactor
                if reactor.http_request[0] in ('GET', 'HEAD', 'DELETE'):
                        # finalize requests without a MIME body now!
                        return self.mime_collector_finalize ()

                # finalize POST and PUT when their body is collected, or
                # close the connection for reason of unimplemented 
                # method (do not waiste bandwith on bogus file uploads).
                #
                if reactor.mime_collector_body == None:
                        reactor.mime_producer_headers[
                                'Connection'
                                ] = 'close'
                        reactor.http_response = 501
                        return self.mime_collector_finalize ()
                        #
                        # 501 Not Implemented
                        
                # wraps the POST or PUT body collector with the appropriate 
                # decoding collectors, and continue ...
                #
                return self.http_collector_continue (
                        reactor.mime_collector_body
                        )
                        
        http_collector_continue = http_reactor.http_collector_continue

        def mime_collector_finalize (self):
                # reset the channel's and MIME collector's state
                self.set_terminator ('\r\n\r\n')
                self.mime_collector_headers = \
                        self.mime_collector_lines = \
                        self.mime_collector_body = None
                # finalize the current HTTP request
                reactor = self.http_reactor # del self.http_reactor ?
                reactor.http_handler.http_finalize (reactor)
                # Complete the HTTP response producer
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
                # code. Then initiate send decide wether or not to close 
                # when done ...
                #
                reactor.mime_producer_lines = mime_headers.lines (
                        reactor.mime_producer_headers
                        )
                reactor.mime_producer_lines.insert (0, 'HTTP/%s %d %s\r\n' % (
                        self.http_version, reactor.http_response,
                        self.HTTP_SERVER_RESPONSES[reactor.http_response]
                        ))
                self.handle_write ()
                if reactor.mime_collector_headers.get (
                        'connection'
                        ) != 'keep-alive':
                        self.close_when_done ()
                # ... finally, log the response's first line.
                reactor.log (reactor.mime_producer_lines[0][:-2], 'response')
                self.http_reactor = None
                return False

        HTTP_SERVER_RESPONSE = (
                '<html><head><title>Error</title></head>'
                '<body><h1>%d %s</h1><pre>%s</pre></body></html>'
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
            
        # Support for stalled producers is a requirement for programming
        # asynchronous peer. It is also a practical solution for simple 
        # asynchronous pipelining of threaded requests. For instance it
        # may be used to thread an HTTP/1.1 requests and push a stalled
        # producer back to the browser that will "produce" as the request
        # progresses, as it thunks data to produce via the select_trigger.


# A Static Cache Root

def http_log (self, reactor):
        loginfo.log (netstring.netstrings ((
                reactor.http_channel.addr,
                reactor.http_request,
                reactor.http_response
                )))

def none (): pass
            
class HTTP_cache (loginfo.Loginfo, finalization.Finalization):

        synchronizer = None
        synchronizer_size = 2
                
        def __init__ (self, path): #, host):
                self.http_path = path
                # self.http_host = host
                self.http_cached = {}
                synchronizer.synchronized (self)
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
                if teed == None:
                        self.synchronized ((
                                self.sync_stat, (reactor, filename)
                                ))
                        return True
        
                reactor.mime_producer_headers.update (teed.mime_headers)
                reactor.mime_producer_body = producer.Tee_producer (teed)
                reactor.http_response = 200
                return False
        
        def http_urlpath (self, reactor):
                return urllib.unquote (reactor.http_uri[2])
        
        http_finalize = http_log
        
        def sync_stat (self, reactor, filename):
                try:
                        result = os.stat (filename)
                except:
                        result = None
                self.select_trigger ((
                        self.async_stat, (reactor, filename, result)
                        ))
        
        def async_stat (self, reactor, filename, result):
                if result == None or not stat.S_ISREG (result[0]):
                        reactor.http_response = 404
                        reactor.http_channel.http_continue (reactor)
                        return
                
                teed = synchronizer.Synchronized_open (filename, 'rb')
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
                reactor.mime_producer_body = producer.Tee_producer (teed)
                reactor.http_response = 200
                self.http_cached[filename] = weakref.ref (teed)
                reactor.http_channel.http_continue (reactor)
                


# The HTTP Server method and variants
        
def http_accept (server, channel):
        channel.http_server = server
        channel.log ('accepted ip="%s" port="%d"' % channel.addr, 'info')
        
def http_continue (server, reactor):
        handler = server.http_hosts.get (
                reactor.mime_collector_headers.get ('host')
                )
        if handler == None:
                reactor.http_response = 404 # Not Found
                return False

        reactor.http_handler = handler
        return handler.http_continue (reactor)

def http_close (server, channel):
        channel.http_server = None

def http_stop (self):
        "called once the server stopped, assert debug log and close"
        self.http_hosts = None
        self.log ('stop', 'info')
        

class HTTP_local (tcp_server.TCP_server):

        def __repr__ (self):
                return 'http-local-server id="%x"' % id (self)

        TCP_SERVER_CHANNEL = HTTP_server_channel
        tcp_server_clients_limit = 64
        
        tcp_server_accept = http_accept
        tcp_server_close = http_close
        http_continue = http_continue
        tcp_server_stop = http_stop
        

class HTTP_private (tcp_server.TCP_server_limit):

        def __repr__ (self):
                return 'http-private-server id="%x"' % id (self)

        TCP_SERVER_CHANNEL = HTTP_server_channel
        tcp_server_clients_limit = 2
        
        tcp_server_accept = http_accept
        tcp_server_close = http_close
        http_continue = http_continue
        tcp_server_stop = http_stop
        

class HTTP_public (tcp_server.TCP_server_throttle):

        def __repr__ (self):
                return 'http-public-server id="%x"' % id (self)

        TCP_SERVER_CHANNEL = HTTP_server_channel
        tcp_server_clients_limit = 1
        
        tcp_server_accept = http_accept
        tcp_server_close = http_close
        http_continue = http_continue
        tcp_server_stop = http_stop


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
        return root, ip, port, host


if __name__ == '__main__':
        import sys
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
        if ip.startswith ('127.'):
                server = HTTP_local ((ip, port))
        elif ip.startswith ('192.168.') or ip.startswith ('10.') :
                server = HTTP_private ((ip, port))
        else:
                server = HTTP_public ((ip, port))
        server.http_hosts = dict ([
                (h, HTTP_cache (p)) 
                for h, p in http_hosts (root, host, port)
                ])
        server.async_catch = async_loop.async_catch
        async_loop.async_catch = server.tcp_server_catch
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
#
# A Static Web Cache
#
# The http_server.py module implements a simple filesystem web service
# that publishes static files from a folder for a named host and address:
#
#        http_server.py [.] [127.0.0.1[:80]] [127.0.0.1]
#
# by default the current directory is served at
#
#        http://127.0.0.1/
#
# The web server acts like a lean filesystem cache, globbing in memory the 
# web as it is served, then throwing it as fast as possible. In effect it
# behaves like a busy-body cache whose memory consumption depends on the 
# parameters set for the garbage gollector of the CPython VM.
#
#
# Allegra PRESTo!
#
# If you need a web application server by yesterday, there's Allgra PRESTo
# and a web prompt from which to test and learn about Allegra's lower-level
# HTTP implementation.
#
# Eventually, once applied, it should be simple to reuse http_server.py and
# derive specialized HTTP protocol implementations other than a network
# file system (and there are many others such as Gnutella, RSS and all 
# protocols piggy-backed on HTTP).
#
# Each virtual host is expected has only one handler implementation for
# each phase of the HTTP protocol. It can delegate a request but must do 
# so explicitely. 
#
# The rational is that Allegra's HTTP server is truly a library to develop
# statefull distributed web applications, not an HTTP dispatcher for stateless
# and consolidated web services. This is not a library to develop an Apache-
# like server. This module is designed to either develop a special purpose web
# server or a peer host for component, where functions are not layered as
# handlers but integrated in Python class methods.
#
#
# Other Applications
#
# For Python developper, Allegra's http_server.py is a big improvement over
# the standard BaseHTTPServer.py as well as Medusa many off-springs, because
# it comes with a ready-made, powerfull and practical API.
#
# It supports non-blocking implementations of all commands of HTTP/1.0 and 
# HTTP/1.1, and may be used to develop many kind of web servers: asynchronous
# network proxies, synchronized services (like a CGI) or a mix of synchronous
# and non-blocking APIs (see presto_http.py implementation of urlencoded REST
# form data POSTed by a web browser).
#
# This is a fully-fledged, high-performance HTTP peer with a low CPU
# footprint, a decent cache, that can limit and throttle network I/O 
# and is well-logged. If you need a low profile but fast public or
# local web server, this simple implementation is available on all
# Python 2.4 supported OS (Window, Linux, MacOSX, etc ...).
#
# Functionnaly, it is not much different than a well configured Apache 2.0
# web server for static files, complete with a limited array of threads
# to ensure non-blocking I/O and a low CPU and memory consumption. It is
# as extensible (you have the sources) and although some of its parts may
# be optimized in a C library, most of it should stay pure Python as its
# applications are better implemented in Python and should be able to access
# the library's interfaces safely and without restrictions.
#
#
# Why Python Matters Here
#
# Because when it comes to integrate and articulate a statefull, large and 
# complex computer application, CPython is the single best implementation
# of a Virtual Machine for something that looks a lot like Lisp but is
# actually written in C and "born" to bind C libraries.
#
# Why write hundreds of thousands lines of C or Java code to integrate a
# monster that is bound to eventually die an horrible death at the first 
# single production bug or unhandled error conditions? Especially if you
# have a single cross-plateform VM optimized in C and published under the
# GPL for a very practical language like Python.
#
# What this module implements in Python is simple instanciation and access of
# five states: the server state, the root state, the async_chat channel state, 
# the reactor's state and the MIME body producer state. And it can do so,
# safely because the CPython VM is a slow but safe bytecode interpreter. Also,
# any application of that thin Python layer is safe to access those states 
# too, allowing thight integration of the application with its host.
#
# Compared to a J2EE or .NET infrastructure, a "pure" Python web peer
# makes a lot of senses once myths about those mega-frameworks have been
# dissipated. Zope is slow because it is both too simple at its core, has
# over-engineered API and a synchronous code base. Yet Medusa was fast and
# its asynchronous design still provide high perfomance to Allegra.
#
# Hosting web application components in a Python shell is practically both
# the safest and the most effective way to do it, provided that it can be
# distributed and implements non-blocking I/O between asynchronous and
# synchronous system or application interfaces.