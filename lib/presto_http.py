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
        finalization, synchronizer, producer, \
        http_server, presto


def presto_decode (urlencoded, result, encoding='UTF-8'):
        "index URL encoded form data into a dictionnary"
        urlencoded = urlencoded.replace ('+', ' ')
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
                                )] = u''
        return result



class PRESTo_http_root (presto.PRESTo_root, finalization.Finalization):

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
                        reactor.presto_rest = presto.presto_rest (
                                reactor.presto_dom.xml_root, reactor, self
                                )
                if (
                        reactor.presto_rest != None and
                        reactor.http_response == 200 and
                        reactor.mime_producer_body == None and 
                        reactor.http_request[0] in ('GET', 'POST')
                        ):
                        # OK but no response body producer, supply one PRESTo!
                        if __debug__:
                                reactor.mime_producer_body = \
                                        presto.presto_producer (
                                                reactor, 'UTF-8',
                                                reactor.http_request_time
                                                )
                        else:
                                reactor.mime_producer_body = \
                                        presto.presto_producer (
                                                reactor, 'UTF-8'
                                                )
                        reactor.mime_producer_headers [
                                'Content-Type'
                                ] = 'text/xml; charset=UTF-8'
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
                reactor.http_channel.http_continue (reactor)
                channel = reactor.http_channel
                if channel.collector_stalled:
                        channel.async_collect ()

        def presto_continue_http (self, reactor):
                # grok the REST vector, set the HTTP response to Ok ...
                #
                if reactor.http_uri[3] != None:
                        reactor.presto_vector = presto_decode (
                                reactor.http_uri[3][1:], {}
                                )
                else:
                        reactor.presto_vector = {}
                reactor.http_response = 200 # Ok
                #
                # ... do the REST of the request ...
                reactor.presto_rest = presto.presto_rest (
                        reactor.presto_dom.xml_root, reactor, self
                        )
                # TODO: move this to the producer part?
                reactor.presto_vector[u'presto-host'] = unicode (
                        reactor.mime_collector_headers.get (
                                'host', ''
                                ), 'UTF-8'
                        )
                reactor.presto_vector[u'presto-path'] = unicode (
                        reactor.http_uri[2] or '', 'UTF-8'
                        )


class PRESTo_form_collector (object):
        
        # a simple collector for URL encoded form data submitted by POST
        
        collector_is_simple = True
        
        def __init__ (self, reactor, buffer):
                self.data = ''
                self.reactor = reactor
                self.buffer = buffer

        def collect_incoming_data (self, data):
                if not (0 < self.buffer < len (data)):
                        self.data += data

        def found_terminator (self):
                # update the reactor's presto vector, REST again and
                # let PRESTo continue to push the HTTP response now.
                #
                self.reactor.http_channel.log (self.data, 'POST')
                presto_decode (self.data, self.reactor.presto_vector)
                return True
                

def presto_form (reactor, buffer=1<<16):
        if (
                reactor.http_request[0] == 'POST' and 
                reactor.mime_collector_body == None
                ):
                reactor.mime_collector_body = PRESTo_form_collector (
                        reactor, buffer
                        )
                return True
                #
                # handle POST: set a URL encoded form data collector of 
                # maximum 64KB in length as the request's MIME body
                # collector. when collected, it will decode itself and
                # call PRESTo's REST function to call back this method

        return False
        #
        # handle GET and the POSTed form data
        #
        #
        # Synopsis in a PRESTo method:
        #
        # if presto_form (self, reactor):
        #         return # collect URL encoded form data POSTed
        #
        # ... handle the REST request GETed or POSTed ...
        #


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
