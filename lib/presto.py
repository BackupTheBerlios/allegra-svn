# Copyright (C) 2005-2007 Laurent A.V. Szyster
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

"Practical REST objects"

import time, random, os, stat, socket, glob
from urllib import unquote as urldecode
try:
        from hashlib import sha1
except:
        from sha import new as sha1
try:
        import cjson
        json_encode = cjson.encode 
        json_decode = (lambda x: cjson.decode (x, 1))
except:
        pass
        
random.seed ()

from allegra import (
        loginfo, finalization, async_server, producer, collector,
        ip_peer, tcp_server, mime_reactor, http_server, xml_dom, xml_reactor
        )
        
        
def http_404_not_found (reactor, about):
        reactor.http_response (404, (('Connection', 'close'),))
        
def url_query (urlencoded, query_strings):
        "map URL encoded form data to UNICODE keys and values"
        for param in urlencoded.split ('&'):
                if param.find ('=') > -1:
                        name, value = param.split ('=', 1)
                        query_strings[unicode (
                                urldecode (name), 'UTF-8', 'replace'
                                )] = unicode (
                                        urldecode (value), 'UTF-8', 'replace'
                                        )
                elif param:
                        query_strings[unicode (
                                urldecode (param), 'UTF-8', 'replace'
                                )] = True
        return query_strings

def irtd2_identified (reactor, about, salts): 
        pass 
        # test that the IRTD2 cookie exists, has not timed out and 
        # bears a valid signature.

def irtd2_authorize (reactor, about, salts):
        pass

def json_200_ok (reactor, value):
        "Reply with 200 Ok and a JSON body, prevent peer to cache it."
        reactor.http_response (
                200, 
                (('Content-Type', 'application/json'),),
                producer.Simple (json_encode (value))
                )

def xml_200_ok (reactor, dom, content_type='text/xml'): 
        "Reply with 200 Ok and an XML body, allow peer to cache it."
        accept_charsets = mime_headers.preferences (
                reactor.collector_headers, 'accept-charset', 'ASCII'
                )
        if 'utf-8' in accept_charsets:
                encoding = 'UTF-8' # prefer UTF-8 over any other encoding!
        else:
                encoding = accept_charsets[-1].upper ()
        reactor.http_response (
                200, 
                (('Content-Type', ';'.join ((
                        content_type, ('charset=%s' % encoding)
                        ))),),
                xml_reactor.XML_producer (dom, encoding)
                )

def rest_302_redirect (reactor, url): 
        reactor.http_response (302, (('Location', url,)))
        # redirect with a 302 response, log same referer as an error.


class Control (
        xml_dom.Document, loginfo.Loginfo, finalization.Finalization
        ):
        
        json = {}
        
        http_post_limit = 16384 # sweet sixteen 8-bit kilobytes ;-)
        
        def __init__ (self, peer, about):
                self.irtd2_salts = peer.irtd2_salts
                self.xml_root = xml_dom.Element (
                        u"allegra.presto Control", {
                                u"context": about[0],
                                u"subject": about[1],
                                }
                        )

        def __call__ (self, reactor, about):
                if irdt2_identified (reactor, about, self.salts):
                        r = reactor.http_request
                        h = reactor.collector_headers
                        if r[0] == 'GET':
                                if r[2] == None:
                                        return self.http_resource (
                                                reactor, about, h
                                                )

                                return self.json_application (
                                        reactor, about, url_query (r[2], {})
                                        )
                        
                        elif r[0] == 'POST':
                                return self.http_post (reactor, about, h)
                        
                        return self.http_continue (reactor, r, about, h)

                return self.irtd2_identify (reactor, about)
        
        def http_post (self, reactor, about, headers):
                ct = headers.get ('content-type')
                if reactor.collector_body == None:
                        if ct in (
                                'application/json',
                                'www-application/urlencoded-form-data'
                                ):
                                reactor.collector_body = collector.Limited (
                                        self.http_post_limit
                                        )
                        else:
                                reactor.http_response (501) # Not implemented
                        return
                
                if ct == 'application/json':
                        json = json_decode (reactor.collector_body.data)
                elif ct == 'www-application/urlencoded-form-data':
                        json = url_query (reactor.collector_body.data, {})
                else:
                        reactor.http_response (501) # Not implemented
                        return
                
                self.json_application (reactor, about, json)

        def http_continue (self, reactor, request, about, headers):
                reactor.http_response (501) # Not implemented
        
        def irtd2_identify (self, reactor, about):
                "redirect unauthorized agents to the /irtd2 URL."
                rest_302_redirect (reactor, "/irtd2")
        
        def http_resource (self, reactor, about, headers):
                "return an XML producer of itself."
                self.xml_root.xml_children = (
                        '<script><![CDATA[json=', 
                        json_encode (self.json),
                        ']]></script>'
                        )
                xml_200_ok (reactor, self)
        
        def json_application (self, reactor, about, json):
                "return the JSON state as one string"
                json_200_ok (reactor, json)
                
        
class ResourceCache (Control):
        
        resource_path = '.'
        resource_cache = {}
        
        def http_resource (self, reactor, about, headers):
                teed = self.resource_cache.get (about)
                if teed != None:
                        reactor.http_response (
                                200, teed.mime_headers, producer.Tee (teed)
                                )
                        return False

                if len (about) < 3:
                        pass # list a directory and cache the result
                
                filename = '/'.join ((self.resource_path, about[2]))
                try:
                        result = os.stat (filename)
                except:
                        result = None
                if result == None or not stat.S_ISREG (result[0]):
                        reactor.http_response (404)
                        return False
                        
                teed = producer.File (open (filename, 'rb'))
                self.resource_cache[about] = teed
                ct, ce = mimetypes.guess_type (filename)
                teed.mime_headers = {
                        'Last-Modified': (
                                time.asctime (time.gmtime (result[7])) + 
                                (' %d' % time.timezone)
                                ),
                        'Content-Type': ct or 'text/html',
                        }
                if ce:
                        teed.mime_headers['Content-Encoding'] = ce
                reactor.http_response (
                        200, teed.mime_headers, producer.Tee (teed)
                        )
                return False
        
        def http_continue (self, reactor, command, about, headers):
                if reactor.http_request[0] != 'HEAD':
                        reactor.http_response (405) # Method Not Allowed 
                else:
                        reactor.http_response (501) # Not implemented
                        #
                        # TODO: add support for HEAD
        

class Listen (async_server.Listen):
        
        irtd2_salts = [''.join ((
                chr(o) for o in random.sample (
                        xrange (ord ('0'), ord ('z')), 20
                        )
                )) for x in range (2)]

        def __init__ (self, path, addr, precision):
                async_server.Listen.__init__ (
                        self, http_server.Dispatcher, addr, 
                        min (precision, 1.0), 
                        tcp_server.LISTEN_MAX, 
                        socket.AF_INET
                        )
                self.presto_path = path
                self.presto_modules = {}
                self.presto_cached = {}
        
        def presto_dir (self):
                "list all source modules's name found in modules/"
                return (os.path.basename (n) for n in glob.glob (
                        '%s/*.py' % self.presto_path
                        ))

        def presto_load (self, filename):
                "load a named Python source module"
                if self.presto_modules.has_key (filename):
                        self.presto_unload (filename)
                name, ext = os.path.splitext (filename)
                try:
                        module = imp.load_source (name , '/'.join ((
                                self.presto_path, filename
                                )))
                except:
                        return self.loginfo_traceback ()
                assert None == self.log (
                        'load filename="%s" id="%x"' % (
                                filename, id (module)
                                ), 'debug'
                        )

                self.presto_cached.update ((
                        (about, Control (self.irtd2_salts))
                        for about, Control in module.controllers.keys ()
                        if not self.presto_cached.has_key (about)
                        ))
                self.presto_modules[filename] = module

        def presto_unload (self, filename):
                "unload a named Python module"
                module = self.presto_modules.get (filename)
                if module == None:
                        return
                        
                assert None == self.log (
                        'unload filename="%s" id="%x"' % (
                                filename, id (module)
                                ), 'debug'
                        )
                for about in module.controllers.keys ():
                        del self.presto_cached[about]
                del self.presto_modules[filename]
        
        def http_continue (self, reactor):
                uri = (reactor.http_uri[2]).split ('/', 2)
                uri[0] = reactor.collector_headers.get (
                        'host', u""
                        )
                about = reactor.uri_about = tuple ((
                        unicode (urldecode (token), 'UTF-8')
                        for token in uri
                        ))
                try:
                        # context, subject and maybe predicate 
                        # || http://host/folder || http://host/folder/file
                        controller = self.presto_cached[about] 
                except:
                        if len (about) > 2:
                                about = (about[0], about[1])
                        else:
                                about = (about[0],)
                        try:
                                # context and subject || http://host/folder
                                controller = self.presto_cached[about] 
                        except:
                                controller = http_404_not_found

                return controller (reactor, about)
