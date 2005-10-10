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

import os, glob
from urllib import unquote, unquote_plus

from allegra.loginfo import Loginfo
from allegra.producer import Simple_producer
from allegra.mime_collector import mime_headers_options
from allegra.http_server import HTTP_root
from allegra.presto import PRESTo_root, presto_rest, presto_producer


def presto_decode (urlencoded_form_data, result, encoding='UTF-8'):
        urlencoded_form_data = urlencoded_form_data.replace ('+', ' ')
        for param in urlencoded_form_data.split ('&'):
                if param.find ('=') > -1:
                        name, value = param.split ('=', 1)
                        result[unicode (
                                unquote (name), encoding, 'replace'
                                )] = unicode (
                                        unquote (value), encoding, 'replace'
                                        )
                elif param:
                        result[unicode (
                                unquote (param), encoding, 'replace'
                                )] = u''
        return result


class PRESTo_http_root (PRESTo_root, HTTP_root):
        
        def __init__ (self, path):
                PRESTo_root.__init__ (self, path)
                HTTP_root.__init__ (self, path)
                
        def __repr__ (self):
                return '<presto-http-root path="%s"/>' % self.presto_path

        def http_match (self, reactor):
                # Direct Cache "Hit"
                if self.presto_dom (reactor, reactor.http_uri[2]):
                        return True
                        
                # Cached Folders "Catch"
                if self.presto_folder (reactor, reactor.http_uri[2], '/'):
                        return True
                
                # Persistent HTTP root filesystem match, load to cache
                if HTTP_root.http_match (self, reactor, ''): # no default!
                        self.presto_cache (
                                reactor,
                                reactor.http_uri[2],
                                reactor.http_handler_filename
                                )
                        return True
                        
                return False
                
        
class PRESTo_handler (Loginfo):
        
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
                return '<presto-handler/>'
                                
        def http_match (self, reactor):
                reactor.presto_root = self.presto_roots.get (
                        reactor.mime_collector_headers.get ('host')
                        )
                if reactor.presto_root == None:
                        return False

                return reactor.presto_root.http_match (reactor)

        def http_continue (self, reactor):
                method = reactor.http_request[0].upper ()
                if method == 'GET':
                        if reactor.http_uri[3] != None:
                                reactor.presto_vector = presto_decode (
                                        reactor.http_uri[3][1:], {}
                                        )
                        else:
                                reactor.presto_vector = {}
                else:
                        reactor.http_response = 405
                        reactor.presto_root = reactor.presto_dom = None
                        return
                        
                result = presto_rest (reactor, self)
                if reactor.mime_producer_body == None:
                        reactor.presto_vector[u'presto-host'] = unicode (
                                reactor.mime_collector_headers.get ('host', ''),
                                'UTF-8'
                                )
                        reactor.presto_vector[u'presto-path'] = unicode (
                                reactor.http_uri[2] or '', 'UTF-8'
                                )
                        if __debug__:
                                reactor.mime_producer_body = presto_producer (
                                        reactor, result, 'UTF-8',
                                        reactor.http_request_time
                                        )
                        else:
                                reactor.mime_producer_body = presto_producer (
                                        reactor, result, 'UTF-8'
                                        )
                        reactor.mime_producer_headers [
                                'Content-Type'
                                ] = 'text/xml; charset=UTF-8'
                        reactor.http_response = 200
                reactor.presto_root = reactor.presto_dom = None
                #
                # Note that http_presto.py only supports UTF-8 as encoding
                # for XML. I don't expect Allegra to be used with something
                # else than Firefox for now. However, upgrading to a public
                # web peer implies either public UTF-8 implementation or
                # "downgrading" to the 7bit ASCII charset (and XML character
                # references).


# TODO: add support for POST (URLencoded and MULTIPART) in http_server.py
#       and reflect changes here.


if __name__ == '__main__':
        import sys
        sys.stderr.write (
                'Allegra PRESTo'
                ' - Copyright 2005 Laurent A.V. Szyster'
                ' | Copyleft GPL 2.0'
                '\n\n...\n'
                )
        from allegra import async_loop
        from allegra.http_server import HTTP_server, HTTP_handler
        presto_root = './presto'
        http_root = './http'
        if len (sys.argv) > 1:
                ip, port = sys.argv[1].split (':')
        else:
                ip, port = ('127.0.0.1', '80')
        HTTP_server (
                [PRESTo_handler (presto_root), HTTP_handler (http_root)],
                ip, int (port)
                )
        try:
                async_loop.loop ()
        except:
                async_loop.loginfo.loginfo_traceback ()


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
# You will find a module manager implemented as a REST module and XML peerlet
# in the two presto.* files:
#
#        ./rest/127.0.0.1/presto.py
#        ./rest/127.0.0.1/presto.xml
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
# where an instance on the path
#
#        /folder
#
# matches or not requests for
#
#        /folder/this/and/that?...
#
# to handle them. Simply implement the interface
#
#        presto_cache ("/this/and/that")
#
# to return None if no match is found or an XML string for the DOM to
# instanciate, cache and to which to transfer control.
#
