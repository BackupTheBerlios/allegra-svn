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

from allegra import \
        netstring, loginfo, async_loop, \
        finalization, synchronizer, collector, producer, \
        mime_headers, http_server, presto


class PRESTo_http_root (presto.PRESTo_root, finalization.Finalization):
        
        "An implementation of PRESTo interfaces for HTTP/1.1 servers"

        synchronizer = None
        synchronizer_size = 2
        
        def __init__ (self, path, host=None, port=80):
                if port == 80:
                        self.http_host = host
                else:
                        self.http_host = '%s:%d' % (host, port)
                presto.PRESTo_root.__init__ (self, path)
                synchronizer.synchronized (self)
                
        def __repr__ (self):
                return 'presto-http-cache path="%s"' % self.presto_path
                
        def http_continue (self, reactor):
                reactor.presto_path = urllib.unquote (reactor.http_uri[2])
                if self.presto_dom (reactor):
                        self.presto_continue_http (reactor)
                        return False
                
                self.synchronized ((self.sync_stat, (
                        reactor, self.presto_path + reactor.presto_path
                        )))
                return True

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
                        self.async_stat, (reactor, filename, result)
                        ))
        
        def async_stat (self, reactor, filename, result):
                if result == None or not stat.S_ISREG (result[0]):
                        reactor.presto_rest = None
                        reactor.http_response = 404
                        reactor.http_channel.http_continue (reactor)
                        return

                self.presto_cache (reactor, filename)
                
        def presto_continue (self, reactor):
                self.presto_continue_http (reactor)
                channel = reactor.http_channel
                channel.http_continue (reactor)
                if channel.collector_stalled:
                        channel.async_collect ()
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


def presto_decode (urlencoded, result, encoding='UTF-8'):
        "index URL encoded form data into a dictionnary"
        for param in urlencoded.split ('&'):
                if param.find ('=') > -1:
                        name, value = param.split ('=', 1)
                        result[unicode (
                                urllib.unquote (name), encoding, 'replace'
                                )] = unicode (
                                        urllib.unquote (value), encoding,
                                        'replace'
                                        )
                elif param:
                        result[unicode (
                                urllib.unquote (param), encoding, 'replace'
                                )] = True
        return result


def presto_vector (urlencoded, interfaces, vector, encoding='UTF-8'):
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
                elif param:
                        name = unicode (urllib.unquote (
                                param
                                ), encoding, 'replace')
                        if name in interfaces:
                                vector[name] = True


# Functions that completes the HTTP response

def rest_response (reactor, result, response):
        encoding = mime_headers.preferences (
                reactor.mime_collector_headers, 'accept-charset', 'ascii'
                )[-1]
        reactor.mime_producer_body = presto.presto_producer (
                reactor.presto_dom,
                reactor.presto_vector,
                result, 
                encoding
                )
        reactor.mime_producer_headers [
                'Content-Type'
                ] = 'text/xml; charset=%s' % encoding
        reactor.http_response = response


def rest_benchmark (reactor, result, response):
        encoding = mime_headers.preferences (
                reactor.mime_collector_headers, 'accept-charset', 'ascii'
                )[-1]
        reactor.mime_producer_body = presto.presto_benchmark (
                reactor.presto_dom,
                reactor.presto_vector,
                result,
                encoding, 
                presto.PRESTo_benchmark (reactor.http_request_time)
                )
        reactor.mime_producer_headers [
                'Content-Type'
                ] = 'text/xml; charset=%s' % encoding
        reactor.http_response = response
        # TODO: handle different character encoding than ASCII
                
if __debug__:
        rest = rest_benchmark
else:
        rest = rest_response        


def get_method (component, reactor):
        if reactor.http_request[0] != 'GET':
                reactor.http_response = 405 # Method Not Allowed
                return

        if component.xml_attributes:
                reactor.presto_vector.update (component.xml_attributes)
        if reactor.http_uri[3] and component.presto_interfaces:
                presto_vector (
                        reactor.http_uri[3][1:].replace ('+', ' '),
                        component.presto_interfaces,
                        reactor.presto_vector
                        )
        method = component.presto_methods.get (
                reactor.presto_vector.get (u'PRESTo')
                )
        if method == None:
                rest (reactor, '<presto:presto/>', 200)
        else:
                rest (reactor, presto.presto_rest (
                        method, component, reactor
                        ), 200)
        

def post_method (component, reactor):
        if reactor.mime_collector_body == None:
                if (
                        reactor.http_request[0] == 'POST' and
                        reactor.mime_collector_headers [
                                'content-type'
                                ] == 'application/x-www-form-urlencoded'
                        ):
                        reactor.mime_collector_body = \
                                collector.Limited_collector (1<<16)
                        # set a limited collector of  maximum 64KB in length
                        # as the request's MIME body collector, ...
                else:
                        reactor.http_response = 405 # Method Not Allowed
                return
                
        if component.xml_attributes:
                reactor.presto_vector.update (component.xml_attributes)
        if reactor.mime_collector_body.data and component.presto_interfaces:
                presto_vector (
                        reactor.mime_collector_body.data.replace ('+', ' '),
                        component.presto_interfaces,
                        reactor.presto_vector
                        )
        method = component.presto_methods.get (
                reactor.presto_vector.get (u'PRESTo')
                )
        if method == None:
                rest (reactor, '<presto:presto/>', 200)
        else:
                rest (reactor, presto.presto_rest (
                        method, component, reactor
                        ), 200)
        

def form_method (component, reactor):
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
                                component.presto_interfaces,
                                reactor.presto_vector
                                )
        elif (
                reactor.http_request[0] == 'POST' and
                reactor.mime_collector_headers ['content-type'].startswith (
                        'application/x-www-form-urlencoded'
                        )
                ):
                reactor.mime_collector_body = \
                        collector.Limited_collector (0)
                return
        
        elif reactor.http_request[0] == 'GET':
                if component.xml_attributes:
                        reactor.presto_vector.update (
                                component.xml_attributes
                                )
                if reactor.http_uri[3] and component.presto_interfaces:
                        presto_vector (
                                reactor.http_uri[3][1:].replace ('+', ' '),
                                component.presto_interfaces,
                                reactor.presto_vector
                                )
        else:
                reactor.http_response = 405 # Method Not Allowed
                return
        
        method = component.presto_methods.get (
                reactor.presto_vector.get (u'PRESTo')
                )
        if method == None:
                rest (reactor, '<presto:presto/>', 200)
        else:
                rest (reactor, presto.presto_rest (
                        method, component, reactor
                        ), 200)


def post_multipart (component, reactor):
        if reactor.mime_collector_body == None:
                if (
                        reactor.http_request[0] == 'POST' and
                        reactor.mime_collector_headers [
                                'content-type'
                                ].startswith ('multipart/form-data')
                        ):
                        reactor.mime_collector_body = \
                                mime_collector.MULTIPART ()
                else:
                        reactor.http_response = 405 # Method Not Allowed
        else:
                pass
                
                
if __name__ == '__main__':
        import sys
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
        server.async_catch = async_loop.async_catch
        async_loop.async_catch = server.tcp_server_catch
        async_loop.loop ()
        
        
# Note about this implementation
#
# Allegra's PRESTo/HTTP peer dispatches REST request to Python instances
# loaded from XML files. It also supports a URL encoded form data POST and 
# provides a web file cache component:
#
#        <presto:cache root="./path"/>
#
# to serve stylesheets and other static resources.
#
# Practically, http_presto.py delivers the minimal set of functions required
# by a web application peer: dispatch HTTP requests to an instance method; 
# support GET and POST of HTML form; serve static files like stylesheets,
# JavaScript libraries and documentation.
#
# For database, metabase and distributed applications support, see the
# presto_bsddb.py and presto_pns.py modules which provide additional 
# features and complete the stack of interfaces required to develop
# distributed web applications.
#
#
# No default REST response
#
# The rational is that the PRESTo handler leaves the choice and
# responsability of the MIME body collector to the instance's
# method called. So that components can themselves pick up from
# a variety of protocols like SOAP or XML/RPC, without making
# PRESTo's HTTP handler more complex.
#
# The benefit for applications developpers is the ability to
# control effectively how input is collected and process data as 
# it is collected. Validating, transcoding and parsing data can be 
# integrated differently and optimaly for each method, and each of
# these high-profile processes may them be optimized individually
# if they are not allready by Python's builtins.
#
# Beyond support for all kind of RPC scheme developped on top of 
# HTTP it effectively matters that a POST, PRESTo's way to handle
# collected MIME bodies, also provides Web media developpers with
# a practical interface.
#
# Lets take the example of a Multipart MIME file upload. Its body
# aggregates encoded form data for the POST request as well as one
# or more parts. Now suppose that one or all of those parts must be
# processed asap, for instance to check an MPEG video header and
# validate the attached XML description and set a low limit to the
# parts size *before* waisting 300MB of bandwith and half and hour
# of everybody's time!
#
# Practically, by default a PRESTo HTTP peer drops any POST request
# and close the session when this interface is accessed but not
# implemented. Allegra provides a simple collector for URL encoded
# REST request, it is up to developpers to provide their own for
# their own application of HTTP's POST command.#