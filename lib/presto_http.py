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

import os, stat, glob, urllib

from allegra import (
        netstring, loginfo, async_loop, finalization, thread_loop, 
        collector, producer, mime_headers, http_server, presto
        )


class PRESTo_http_root (presto.PRESTo_root, finalization.Finalization):
        
        "An implementation of PRESTo interfaces for HTTP/1.1 servers"

        synchronizer = None
        synchronizer_size = 2 
        #
        # First os.stat should be fast enough not to require more than two
        # threads for all roots. Second, it won't hurt having a bottleneck
        # on cache misses and the filesystem look they entail. Preventing
        # potential DoS exploit of that bottleneck is a general precaution
        # against spammers.
                
        def __init__ (self, path, host=None, port=80):
                if port == 80:
                        self.http_host = host
                else:
                        self.http_host = '%s:%d' % (host, port)
                presto.PRESTo_root.__init__ (self, path)
                thread_loop.synchronized (self)
                
        def __repr__ (self):
                return 'presto-http-cache path="%s"' % self.presto_path
                
        def http_continue (self, reactor):
                reactor.presto_path = urllib.unquote (reactor.http_uri[2])
                if self.presto_route (reactor):
                        defered = reactor.presto_dom.presto_defered 
                        if defered == None:
                                self.presto_continue_http (reactor)
                                return False
                        
                        defered.append ((
                                self.presto_continue, (reactor, )
                                ))
                        return True
                
                self.synchronized ((self.sync_stat, (
                        reactor, self.presto_path + reactor.presto_path
                        )))
                return True # sure, True: this will be continued ...

        def http_finalize (self, reactor):
                if reactor.mime_collector_body != None:
                        self.presto_continue_http (reactor)
                http_server.http_log (self, reactor)

        def sync_stat (self, reactor, filename):
                try:
                        result = os.stat (filename)
                except:
                        result = None
                self.select_trigger ((
                        self.async_stat, (reactor, result)
                        ))
        
        def async_stat (self, reactor, result):
                if result == None or not stat.S_ISREG (result[0]):
                        reactor.http_response = 404
                        reactor.http_channel.http_continue (reactor)
                        return

                self.presto_dom (reactor)
                
        def presto_continue (self, reactor):
                self.presto_continue_http (reactor)
                channel = reactor.http_channel
                channel.http_continue (reactor)
                channel.collector_stalled = False
                #
                # Resume collection of the async_chat buffer
                # stalled while loading the synchronized XML
                # instance in the cache.

        def presto_continue_http (self, reactor):
                dom = reactor.presto_dom
                reactor.presto_vector = {
                        u'presto-path': unicode (dom.presto_path, 'UTF-8')
                        }
                try:
                        dom.xml_root.presto (reactor)
                except:
                        self.loginfo_traceback ()
                        reactor.http_response = 500 # Server Error


def presto_decode (urlencoded, vector, encoding='UTF-8'):
        "map URL encoded form data to UNICODE keys and values"
        for param in urlencoded.split ('&'):
                if param.find ('=') > -1:
                        name, value = param.split ('=', 1)
                        vector[unicode (
                                urllib.unquote (name), encoding, 'replace'
                                )] = unicode (
                                        urllib.unquote (value), encoding,
                                        'replace'
                                        )
                elif param:
                        vector[unicode (
                                urllib.unquote (param), encoding, 'replace'
                                )] = True
        return vector


# You can do pretty much what you want with an HTTP request from within the
# component presto implementation: handle HTTP/1.1 extended methods, collect
# and process file uploads synchronously or set the response's headers and
# body. However, the bigger part of a web application ban best be reduced
# to its REST. Below is PRESTo's implementation of REST for URL encoded form
# data submitted by POST and GET methods.
#
# Feel free to implement your own flavor of AJAX, RPC or whatever crazy
# template language you happen to like. I'll stay with the stable stack:
#
#        XML + XSLT = XHTML + CSS + JavaScript
#
# It saves PRESTo the burden of display rendering, and saves its 
# applications all the troubles that inevitably arise from the use of
# client/server designs for a stateless protocol like HTTP.
#
# I consider AJAX the harmfull return of the C/S zombie. Web pages with 
# JavaScript user interface automation is nice, but holding the full
# application state in a crash-prone browser and an insecure PC is not
# a very good idea. If cookies aren't enough


def presto_vector (
        urlencoded, vector, interfaces, encoding='UTF-8', strict=True
        ):
        "map only URL encoded form data declared in the interfaces set"
        for param in urlencoded.split ('&'):
                if param.find ('=') > -1:
                        encoded, value = param.split ('=', 1)
                        name = unicode (urllib.unquote (
                                encoded
                                ), encoding, 'replace')
                        if name in interfaces:
                                vector[name] = unicode (urllib.unquote (
                                        value
                                        ), encoding, 'replace')
                        elif strict:
                                return
                        
                elif param:
                        name = unicode (urllib.unquote (
                                param
                                ), encoding, 'replace')
                        if name in interfaces:
                                vector[name] = True
                        elif strict:
                                return
                        
        return vector
        #
        # The rational for such function is that a URL query string might be 
        # irrelevant to its handler, which should waiste no time unquoting
        # and decoding such bogus argument. When handling POSTed form, an
        # application should be guarded against malicious attacks like a
        # flood of 

# Functions that completes PRESTo's asynchronous REST response headers and
# body, with or without a benchmark producer:
#
# HTTP/1.1 200 Ok
# Content-Type: text/xml; charset=iso-8859-1
#
# <PRESTo 
#    presto="http://presto" 
#    ... request/response state ...
#    >
#    ... result: byte string, unicode, XML element or generator ...
#    <instance/>
#    <!-- ... benchmarks ... -->
# </PRESTo>
#

def rest_response (reactor, result, response):
        charsets = mime_headers.preferences (
                reactor.mime_collector_headers, 'accept-charset', 'ascii'
                )
        if 'utf-8' in charsets:
                encoding = 'UTF-8' # prefer UTF-8 over any other encoding!
        else:
                encoding = charsets[-1].upper ()
        reactor.mime_producer_body = presto.presto_producer (
                reactor.presto_dom, reactor.presto_vector, result, encoding
                )
        reactor.mime_producer_headers [
                'Content-Type'
                ] = 'text/xml; charset=%s' % encoding
        reactor.http_response = response


def rest_benchmark (reactor, result, response):
        charsets = mime_headers.preferences (
                reactor.mime_collector_headers, 'accept-charset', 'ascii'
                )
        if 'utf-8' in charsets:
                encoding = 'UTF-8'
        else:
                encoding = charsets[-1].upper ()
        reactor.mime_producer_body = presto.presto_benchmark (
                reactor.presto_dom, reactor.presto_vector, result, encoding,
                presto.PRESTo_benchmark (reactor.http_request_time)
                )
        reactor.mime_producer_headers [
                'Content-Type'
                ] = 'text/xml; charset=%s' % encoding
        reactor.http_response = response
                
                
if __debug__:
        rest = rest_benchmark
else:
        rest = rest_response


# GET form data, return the REST

def get_rest (component, reactor):
        if reactor.http_request[0] != 'GET':
                reactor.http_response = 405 # Method Not Allowed
                return

        if component.xml_attributes:
                reactor.presto_vector.update (component.xml_attributes)
        if reactor.http_uri[3] and component.presto_interfaces:
                presto_vector (
                        reactor.http_uri[3].replace ('+', ' '),
                        reactor.presto_vector,
                        component.presto_interfaces,
                        )
        method = component.presto_methods.get (
                reactor.presto_vector.get (u'PRESTo')
                )
        if method == None:
                rest (reactor, '<presto xmlns="http://presto/"/>', 200)
        else:
                rest (reactor, presto.presto_rest (
                        method, component, reactor
                        ), 200)
        

# POST form data, return the REST

def post_rest (component, reactor, POST_LIMIT=1<<16):
        if reactor.mime_collector_body == None:
                if (
                        reactor.http_request[0] == 'POST' and
                        reactor.mime_collector_headers [
                                'content-type'
                                ] == 'application/x-www-form-urlencoded'
                        ):
                        reactor.mime_collector_body = \
                                collector.Limited_collector (POST_LIMIT)
                        reactor.http_response = 200
                else:
                        reactor.http_response = 405 # Method Not Allowed
                return
                
        if component.xml_attributes:
                reactor.presto_vector.update (component.xml_attributes)
        if reactor.mime_collector_body.data and component.presto_interfaces:
                presto_vector (
                        reactor.mime_collector_body.data.replace ('+', ' '),
                        reactor.presto_vector,
                        component.presto_interfaces
                        )
        method = component.presto_methods.get (
                reactor.presto_vector.get (u'PRESTo')
                )
        if method == None:
                rest (reactor, '<presto xmlns="http://presto/"/>', 200)
        else:
                rest (reactor, presto.presto_rest (
                        method, component, reactor
                        ), 200)
        

def form_rest (component, reactor, POST_LIMIT=1<<16):
        "GET or POST handler for REST request"
        if reactor.mime_collector_body != None:
                if component.xml_attributes:
                        reactor.presto_vector.update (
                                component.xml_attributes
                                )
                if (
                        reactor.mime_collector_body.data and 
                        component.presto_interfaces
                        ):
                        presto_vector (
                                reactor.mime_collector_body.data.replace (
                                        '+', ' '
                                        ),
                                reactor.presto_vector,
                                component.presto_interfaces
                                )
        elif (
                reactor.http_request[0] == 'POST' and
                reactor.mime_collector_headers ['content-type'].startswith (
                        'application/x-www-form-urlencoded'
                        )
                ):
                reactor.mime_collector_body = \
                        collector.Limited_collector (POST_LIMIT)
                reactor.http_response = 200
                return
        
        elif reactor.http_request[0] == 'GET':
                if component.xml_attributes:
                        reactor.presto_vector.update (
                                component.xml_attributes
                                )
                if reactor.http_uri[3] and component.presto_interfaces:
                        presto_vector (
                                reactor.http_uri[3].replace ('+', ' '),
                                reactor.presto_vector,
                                component.presto_interfaces
                                )
        else:
                reactor.http_response = 405 # Method Not Allowed
                return
        
        method = component.presto_methods.get (
                reactor.presto_vector.get (u'PRESTo')
                )
        if method == None:
                rest (reactor, '<presto xmlns="http://presto/"/>', 200)
        else:
                rest (reactor, presto.presto_rest (
                        method, component, reactor
                        ), 200)


def post_multipart (reactor):
        if reactor.mime_collector_body == None:
                if (
                        reactor.http_request[0] == 'POST' and
                        reactor.mime_collector_headers [
                                'content-type'
                                ].startswith ('multipart/form-data')
                        ):
                        return True

        return False
        
        # Synopsis
        #
        # def presto (component, reactor):
        #        if presto_http.post_multipart (reactor):
        #                ... set a reactor.mime_collector_body ...
        #
        #        ... handle errors or finalize the collected body ...

                
if __name__ == '__main__':
        import sys, time
        t = time.clock ()
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
                'Allegra PRESTo/HTTP'
                ' - Copyright 2005 Laurent A.V. Szyster | Copyleft GPL 2.0',
                'info'
                )
        root, ip, port, host = http_server.cli (sys.argv)
        if ip.startswith ('127.'):
                server = http_server.HTTP_local ((ip, port))
        elif ip.startswith ('192.168.') or ip.startswith ('10.') :
                server = http_server.HTTP_private ((ip, port))
        else:
                server = http_server.HTTP_public ((ip, port))
        server.http_hosts = dict ([
                (h, PRESTo_http_root (p)) 
                for h, p in http_server.http_hosts (root, host, port)
                ])
        if sync_stdio:
                class Sync_stdoe (sync_stdio.Sync_stdoe):
                        def async_prompt_catch (self):
                                self.async_stdio_stop ()
                                server.handle_close ()
                                return True

                Sync_stdoe ().start ()
                #del server
        else:
                server.async_catch = async_loop.async_catch
                async_loop.async_catch = server.tcp_server_catch
                del server
        assert None == loginfo.log (
                'startup seconds="%f"' % (time.clock () - t), 'PRESTo/HTTP'
                )
        async_loop.dispatch ()
        assert None == finalization.collect ()
                        