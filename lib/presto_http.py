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

import os, glob, urllib

from allegra import \
        loginfo, async_loop, producer, mime_reactor, http_server, presto


def presto_decode (urlencoded_form_data, result, encoding='UTF-8'):
        "index URL encoded form data into a dictionnary"
        urlencoded_form_data = urlencoded_form_data.replace ('+', ' ')
        for param in urlencoded_form_data.split ('&'):
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



class PRESTo_http_root (presto.PRESTo_root, http_server.HTTP_root):
        
        def __init__ (self, path):
                http_server.HTTP_root.__init__ (self, path)
                presto.PRESTo_root.__init__ (self, path)
                
        def __repr__ (self):
                return 'presto-http-root host="%s"' % self.http_host

        def http_match (self, reactor):
                url = reactor.http_uri[2]
                # Direct Cache "Hit"
                if self.presto_dom (reactor, url):
                        return True
                        
                # Cached Folders "Catch"
                if self.presto_folder (reactor, url, '/'):
                        return True
                
                # Persistent HTTP root filesystem match, load to cache
                if http_server.HTTP_root.http_match (self, reactor, ''): 
                        self.presto_cache (
                                reactor, url,
                                reactor.http_handler_filename
                                )
                        return True
                        
                return False
                
        
def presto_http_continue (reactor, method, result):
        if (
                reactor.mime_producer_body == None and 
                method in ('GET', 'POST')
                ):
                # if there is no body, supply one PRESTo!
                if __debug__:
                        reactor.mime_producer_body = \
                                presto.presto_producer (
                                        reactor, result, 'UTF-8',
                                        reactor.http_request_time
                                        )
                else:
                        reactor.mime_producer_body = \
                                presto.presto_producer (
                                        reactor, result, 'UTF-8'
                                        )
                reactor.mime_producer_headers [
                        'Content-Type'
                        ] = 'text/xml; charset=UTF-8'
        if reactor.http_response == None:
                reactor.http_response = 200 # Ok by default
        #
        # ? reactor.presto_root = reactor.presto_dom = None
        #
        # Note that http_presto.py only supports UTF-8 as encoding
        # for XML. I don't expect Allegra to be used with something
        # else than Firefox for now. However, upgrading to a public
        # web peer implies either public UTF-8 implementation or
        # "downgrading" to the 7bit ASCII charset (and XML character
        # references).


class PRESTo_handler (loginfo.Loginfo):
        
        def __init__ (self, root):
                paths = [r.replace ('\\', '/') for r in glob.glob (root+'/*')]
                self.presto_roots = dict ([
                        (
                                os.path.split (r)[1].replace ('-', ':'), 
                                PRESTo_http_root (r)
                                )
                        for r in paths
                        ])

        def __repr__ (self):
                return 'presto-handler id="%x"' % id (self)
                                
        def http_match (self, reactor):
                reactor.presto_root = self.presto_roots.get (
                        reactor.mime_collector_headers.get ('host')
                        )
                if reactor.presto_root == None:
                        return False

                return reactor.presto_root.http_match (reactor)

        def http_continue (self, reactor):
                # unpack the request's arguments into the reactor's 
                # presto vector, and set the host and path parameters
                #
                method = reactor.http_request[0].upper ()
                if reactor.http_uri[3] != None:
                        reactor.presto_vector = presto_decode (
                                reactor.http_uri[3][1:], {}
                                )
                else:
                        reactor.presto_vector = {}
                reactor.presto_vector[u'presto-host'] = unicode (
                        reactor.mime_collector_headers.get (
                                'host', ''
                                ), 'UTF-8'
                        )
                reactor.presto_vector[u'presto-path'] = unicode (
                        reactor.http_uri[2] or '', 'UTF-8'
                        )
                # do the REST of the request ...
                result = presto.presto_rest (reactor, self)
                if reactor.mime_collector_body != None:
                        return # ... maybe twice ...
                        
                # ... or continue and push the HTTP response now.
                presto_http_continue (reactor, method, result)
                        

class PRESTo_form_collector (object):
        
        # a simple collector for URL encoded form data submitted by POST
        
        __slots__ = ('data', 'reactor', 'logger')
        
        def __init__ (self, logger, reactor, BUFFER_SIZE=0):
                self.data = ''
                self.reactor = reactor
                self.logger =logger

        def collect_incoming_data (self, data):
                if not (0 < BUFFER_SIZE < len (data)):
                        self.data += data

        def found_terminator (self):
                # update the reactor's presto vector, REST again and
                # let PRESTo continue to push the HTTP response now.
                #
                presto_decode (self.data, self.reactor.presto_vector)
                result = presto.presto_rest (self.reactor, self.logger)
                presto_http_continue (self.reactor, 'POST', result)
                # self.reactor = self.logger = None # ? just to be safe
                return True
                

def presto_form (self, reactor):
        if (
                reactor.http_command == 'POST' and 
                reactor.mime_body_collector == None
                ):
                reactor.mime_body_collector = PRESTo_form_collector (
                        self, reactor, 1<<16
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


class PRESTo_http (http_server.HTTP_server):

        def __init__ (self, handlers, ip, port):
                http_server.HTTP_server.__init__ (self, handlers, ip, port)
                if ip == '127.0.0.1':
                        self.tcp_server_clients_limit = 64
                self.async_catch = async_loop.async_catch
                async_loop.async_catch = self.tcp_server_catch
                

if __name__ == '__main__':
        import sys
        if '-d' in sys.argv:
                sys.argv.remove ('-d')
                loginfo.Loginfo_stdio.log = \
                        loginfo.Loginfo_stdio.loginfo_netlines
        loginfo.log (
                'Allegra PRESTo'
                ' - Copyright 2005 Laurent A.V. Szyster | Copyleft GPL 2.0',
                'info'
                )
        presto_root = './presto'
        http_root = './http'
        if len (sys.argv) > 1:
                ip, port = sys.argv[1].split (':')
                if len (sys.argv) > 2:
                        presto_root = sys.argv[2]
                        if len (sys.argv) > 3:
                                http_root = sys.argv[3]
        else:
                ip, port = ('127.0.0.1', '80')
        PRESTo_http ([
                PRESTo_handler (presto_root), 
                http_server.HTTP_handler (http_root)
                ], ip, int (port))
        async_loop.loop ()


# Note about this implementation
#
# This is Allegra's implementation of the HTTP/XML server meme, but without
# the addition of yet another server-side scripting markup language mixing
# HTML and Python. As you will notice, the support of XML features is not very
# developped, but Processing Instructions are passed through the browser, and
# you can use XSLT and CSS stylesheets to present the XML response.
#
# However, nothing prevents developpers to pass their own MIME body producer
# to the HTTP channel, asynchronously, allowing them to mix threaded
# synchronous processes and fast asynchronous process and I/O.
#
# Think of it as a fast and simple host for web XML peerlets ;-)
#
# PRESTo handles REST and AJAX requests and at will use either fast
# asynchronous I/O or threaded synchronous method, none of which blocking
# both types sharing a common asynchronous REST state, with a distinct copy
# of it for each synchronized request.
#
#
# Dynamically (un)loadable Python REST module
#
# The namespace used to map Python class to XML elements depends on the
# hostname the request is intended for. Any Python source file is loaded
# as a module (imported) and the class with an xml_name attribute are
# mapped in the XML namespace associated with the hostname.
#
#
# No Authentication
#
# There is no authentication. It is supposed to listen on your loopback
# localhost address 127.0.0.1 which is considered to be private. Adding
# authentication would require the implementation of SSL/TLS including
# which may be done more simply outside of Allegra using SSL/TLS proxies.
# Real cryptographic authentication requires support for client and server
# certificates and has little public applications.
#
# In any case, Allegra's applications/peerlets may more easely implement
# authentication themselves (using signed cookies or one-time passwords).
#
#
# You can still add HTTP handlers, using a "Folder" paradigm
#
# If your application needs to handle virtual host URI patterns, it should
# register its own handler in the HTTP_server.http_handlers list, inserting
# it between the two default handlers, after PREST and before HTTP static.
#
# However, the most common case for URI pattern is the "folder" paradigm,
# where a requests for
#
#        /folder/this/and/that?...
#
# is walked from the left, looking up for a match of:
#
#        /folder/this/and
#        /folder/this
#        /folder
#
# in the presto root's cache with an xml_root element that implements
# the interface:
#
#        presto_folder
#
# and returns not NULL. There is a limit on the "depth" of folder, stricly
# set to 1, and which should be raised to 3 for the popular:
#
#        /model/controller/view
#
# web API articulation. IMHO, this URL rewriting stuff is just a patch
# and the purpose is rather to support a flat collections of component
# instances that manage their own collection of instances, like
# a BSDDB database or a PNS metabase.
#
#        /~component        # asynchronous, disk I/O is blocking
#        /pns/~component    # asynchronous, network I/O, not blocking
#        /bsddb/~component  # synchronized, disk I/O may be slowing
#
# Those three kind of persistence are enough to support a broad range of 
# applications. BSDDB can manage huge databases (backups) and PNS delivers 
# distributed persistence and semantic on top of the same industrial-strength
# C library.
#