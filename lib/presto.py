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

import types, imp, weakref, time, random, os, stat, socket, glob, re, mimetypes

try:
        from hashlib import sha1
except:
        from sha import new as sha1


def password (
        charset=[i for i in xrange (ord ('0'), ord ('z'))], length=10
        ):
        random.seed ()
        return ''.join ((chr(o) for o in random.sample (charset, length)))
                

from urllib import unquote as urldecode

def urlform_decode (formencoded):
        "map URL encoded form data to UNICODE keys and values"
        query_strings = {}
        for param in formencoded.split ('&'):
                if param.find ('=') > -1:
                        name, value = param.split ('=', 1)
                        query_strings[unicode (
                                urldecode (name), 'UTF-8'
                                )] = unicode (urldecode (value), 'UTF-8')
                elif param:
                        query_strings[unicode (
                                urldecode (param), 'UTF-8'
                                )] = None
        return query_strings

JSON_ATOMS = frozenset ((
        types.NoneType, bool, int, long, float, str, unicode
        ))
JSON_ITERS = frozenset ((list, tuple, set, frozenset))
JSON_TYPES = frozenset (JSON_ATOMS|JSON_ITERS|set((dict,)))
def json_safe (value, walked):
        t = type (value)
        if t in JSON_ATOMS:
                return value # JSON null, boolean, number and string
        
        _id = id (value)
        if _id in walked:
                return
        
        walked.add (_id)
        if t in JSON_ITERS:
                return [json_safe (v, walked) for v in value] # JSON array
        
        elif t == dict:
                return dict ((
                        (unicode (k), json_safe (v, walked)) 
                        for k, v in value.items ()
                        )) # a Python dictionnary is a JSON object
                        
        return repr (value)

try:
        from cjson import encode as json_encode
        from cjson import decode as _decode
        json_decode = (lambda s: _decode (s, 1))
except:
        raise Exception (
                'install cjson, see: '
                'http://cheeseshop.python.org/pypi/python-cjson'
                )


from allegra import (
        netstring, prompt, loginfo, async_loop, finalization,
        producer, collector, async_server,
        ip_peer, tcp_server, mime_headers, mime_reactor, 
        http_server, xml_dom, xml_reactor
        )
        
        
def mime_cache (filename, cache):
        subject = unicode (os.path.basename (filename), 'UTF-8')
        try:
                metadata = os.stat (filename)
        except:
                metadata = None
        if metadata == None or not stat.S_ISREG (metadata[0]):
                return subject, None

        headers = [
                ('Last-Modified', (
                        time.asctime (time.gmtime (metadata[7])) + 
                        (' %d' % time.timezone)
                        )),
                ('Content-length', '%d' % metadata[1])
                ]
        ct, ce = mimetypes.guess_type (filename)
        if ce:
                headers.append ((
                        'Content-Type', 
                        '%s; charset=%s' % (ct or 'text/plain', ce)
                        ))
        else:
                headers.append ((
                        'Content-Type', ct or 'application/octet-stream'
                        ))
        teed = producer.Simple (open (filename, 'rb').read ())
        teed.mime_headers = headers
        cache[subject] = teed
        return subject, teed

if __debug__:
        def mime_cache_weak (fun):
                def decorated (filename, cache):
                        subject, teed  = fun (filename, cache)
                        if teed != None:
                                cache[subject] = weakref.ref (teed)
                        return subject, teed
                        
                return decorated

        mime_cache = mime_cache_weak (mime_cache)

IRTD2_ERRORS = (
        '0 IRTD2 ok', # 0, no errors
        '1 No IRTD2 cookie', # 1
        '2 Invalid IRTD2 cookie value', # 2
        '3 IRTD2 cookie timedout', # 3
        '4 Invalid IRTD2 digest' # 4
        )

def irtd2_identified (http, about, salts, timeout):
        cookies = http.cookies ('IRTD2=')
        try:
                value = cookies.next ()
        except StopIteration:
                return 1 # no IRTD2 cookie
        
        irtd2 = value.split (' ')
        if len (irtd2) != 5:
                return 2 # invalid IRTD2 cookie
        
        now = long (time.time ())
        if not (-1 < now - long (irtd2[2]) < timeout):
                return 3 # timed out IRTD2 cookie
         
        digest = irtd2[4]
        for salt in salts:
                irtd2[4] = salt
                if sha1 (' '.join (irtd2)).hexdigest () == digest:
                        irtd2[2] = str (now) # bytes!
                        irtd2[3] = digest
                        irtd2_identify (http, about, irtd2)
                        return 0 # identified
        
        return 4 # 
        #
        # Test that one IRTD2 cookie exists, has not timed out and bears a 
        # valid signature. Note that I assume that the most specific cookie 
        # is listed first, that "/context/subject" precedes "/context" and
        # that more cookies don't masquerade/merge the authorizations or 
        # identity they carry.
        
def irtd2_identify (http, about, irtd2):
        assert type (irtd2) == list and len (irtd2) == 5
        irtd2[4] = (sha1 (' '.join (irtd2)).hexdigest ())
        http.producer_headers['Set-Cookie'] = (
                'IRTD2=%s; '
                'expires=Sun 17 Jan 2038 19:14:07 GMT; '
                'path=/%s/; domain=.%s.' % (
                        ' '.join (irtd2), about[1], about[0]
                        )
                )
        http.irtd2 = irtd2


def http_head (control, http, about):
        return control.http_resource (http, about, 'HEAD')


def http_get (control, http, about):
        "default continuation for GET: dispatch resource and calls"
        querystring = http.uri[3]
        if querystring == None:
                return control.http_resource (http, about, 'GET')

        return control.json_application (
                http, about, urlform_decode (querystring)
                ) # Web 1.0 & 2.0

def http_post (control, http, about, overrideMIME='application/json'):
        "default continuation for POST: handle JSON and URL encoded form"
        ct = http.collector_headers.get (
                'content-type', overrideMIME
                ).split (';', 1)[0]
        if http.collector_body == None: # no body collector yet ...
                if ct in (
                        'application/json',
                        'www-application/urlencoded-form-data'
                        ): # instanciate one for JSON or URL encoded form 
                        http.collector_body = control.http_collector ()
                        return False # Web 1.0 & 2.0
                
                return control.http_continue (http, about) # or continue.
                
        # body collected, decode the posted JSON or form data ...
        if ct == 'application/json':
                return control.json_application (
                        http, about, json_decode (
                                http.collector_body.data
                                )
                        ) # Web 2.0 is JSON
                        
        elif ct == 'www-application/urlencoded-form-data':
                return control.json_application (
                        http, about, urlform_decode (
                                http.collector_body.data
                                )
                        ) # Web 1.0 is URL form
                        
        return http (500) # Server Error


def http_continue (controller, http, about):
        "reply with 405 Not Implemented and close the connection when done"
        return http (405, http_server.CONNECTION_CLOSE)


def http_404_close (http, about):
        "reply with 404 Not Found and close the connection when done"
        return http (404, http_server.CONNECTION_CLOSE)


def rest_302_redirect (http, about):
        "redirect to the controller's locator in the context of the reactor"
        uri = http.uri[:2]
        uri.append ('/')
        uri.append ((u"/".join (about)).encode ('UTF-8'))
        return http (302, (('Location', ''.join (uri)),))

CONTENT_TYPE_XML = (('Content-Type', 'text/xml; charset=UTF-8'),)

def xml_200_ok (http, dom, content_type='text/xml'): 
        "Reply with 200 Ok and an XML body encoded in UTF-8."
        #accept_charsets = mime_headers.preferences (
        #        reactor.collector_headers, 'accept-charset', 'ASCII'
        #        )
        #if 'utf-8' in accept_charsets:
        #        encoding = 'UTF-8' # prefer UTF-8 over any other encoding!
        #else:
        #        encoding = accept_charsets[-1].upper ()
        return http (200, (
                ('Content-Type', content_type + '; charset=UTF-8'),
                ), xml_reactor.xml_producer_unicode (
                        dom.xml_root, dom.xml_prefixes, dom.xml_pi, 'UTF-8'
                        )
                )


if __debug__:
        CONTENT_TYPE_JSON = ((
                'Content-Type', 'text/javascript; charset=UTF-8'
                ),) # you need this to see what you get ;-)
else:
        CONTENT_TYPE_JSON = ((
                'Content-Type', 'application/json; charset=UTF-8'
                ),)
                
def json_noop (controller, http, about, json):
        return 501 # Not Implemented ;-)

class Control (
        xml_dom.Document, loginfo.Loginfo, finalization.Finalization
        ):

        xml_prefixes = {}
        xml_pi = {}
        
        HTTP = {'HEAD': http_head, 'GET': http_get, 'POST': http_post}
        
        irtd2_salts = [password ()]
        irtd2_timeout = 1<<32 # practically never by default
        
        rest_redirect = u"index.html"

        json_actions = {}
        jsonr_model = None
        
        def __init__ (self, peer, about):
                about_utf8 = [s.encode ('UTF-8') for s in about]
                about_utf8[0] = 'http://' + about_utf8[0]
                self.uri = '/'.join (about_utf8)
                about_utf8[0] = peer.presto_path
                self.presto_path = '/'.join (about_utf8)
                self.xml_root = xml_dom.Element (
                        u"allegra Control", {
                                u"context": about[-2],
                                u"subject": about[-1],
                                }
                        )
                self.json = {}
                self.mime_cache = {}
                if __debug__:
                        null = (lambda: None)
                        def mime_cache_get (name):
                                teed = self.mime_cache.get (name, null) ()
                                if not teed:
                                        subject, teed = mime_cache (
                                                '/'.join ((
                                                        self.presto_path,
                                                        name.encode ('UTF-8')
                                                        )), 
                                                self.mime_cache
                                                )
                                return teed
                        
                        self.mime_cache_get = mime_cache_get
                else:
                        for filename in glob.glob('%s/*' % self.presto_path):
                                try:
                                        mime_cache (filename, self.mime_cache)
                                except:
                                        self.loginfo_traceback ()
                                else:
                                        self.log (filename, 'cached')
                        self.mime_cache_get = self.mime_cache.get
                                        
        def __call__ (self, http, about):
                if (hasattr (http, 'irtd2') or irtd2_identified (
                        http, about, self.irtd2_salts, self.irtd2_timeout
                        ) == 0):
                        return self.HTTP.get (
                                http.request[0], http_continue
                                ) (self, http, about)

                return self.irtd2_identify (http, about)
        
        def http_resource (self, http, about, method):
                u"produce a static MIME response or an dynamic XML string."
                if len (http.uri_about) == 3:
                        if http.uri_about[-1] == u"":
                                # context/subject/ -> 302 context/subject
                                about = list (http.uri_about)
                                about[-1] = self.rest_redirect
                                return rest_302_redirect (
                                        http, about[1:]
                                        )
                        
                        # context/subject/predicate -> 200 Ok | 404 Not Found
                        teed = self.mime_cache_get (http.uri_about[2])
                        if teed:
                                if method == 'GET':
                                        return http (
                                                200, 
                                                teed.mime_headers, 
                                                producer.Tee (teed)
                                                ) # Ok
                                                
                                elif method == 'HEAD':
                                        return http (
                                                200, teed.mime_headers
                                                )
                                
                        return rest_302_redirect (http, about[1:])
                                        
                # context/subject -> 200 Ok XML
                if method == 'GET':
                        return xml_200_ok (http, self) # what else?
                
                elif method == 'HEAD':
                        return http (200, CONTENT_TYPE_XML)
                        #
                        # if you care to ask for HEAD, expect to accept UTF-8
                        
                return self.http_continue (http, about)
        
        def http_collector (self):
                return collector.Limited (16384)
                # sweet sixteen 8-bit kilobytes ;-)
        
        def json_application (self, http, about, json):
                u"try to dispatch requests to actions, produce a JSON object"
                try:
                        status = self.json_actions.get(
                                http.uri_about[-1], json_noop
                                ) (self, http, about, json)
                except:
                        json[u"exception"] = self.loginfo_traceback ()
                        return http (
                                500, CONTENT_TYPE_JSON, producer.Simple (
                                        json_encode (json)
                                        )
                                )
                
                return http (
                        status, CONTENT_TYPE_JSON, producer.Simple (
                                json_encode (json)
                                )
                        )
                                
        def irtd2_identify (self, http, about):
                u"identify an anonymous user"
                irtd2_identify (http, about, [
                        password (), '', '%d' % time.time (), '',
                        self.irtd2_salts[0]
                        ])
                return self (http, about) # recurse through __call__ ...
        
        def http_continue (self, http, about):
                "405 Method Not Allowed"
                return http (405, http_server.CONNECTION_CLOSE)


HTTP_URI = re.compile (
        '(?:([^:]+://)([^/]+))?(/(?:[^?#]+)?)(?:[?]([^#]+)?)?(#.+)?'
        )

class Listen (async_server.Listen):

        presto_root = {}
        
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
                self.presto_root[path] = weakref.ref (self)
        
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
                        controllers = [
                                (about, Control (self, about))
                                for about, Control 
                                in module.controllers.items ()
                                if not self.presto_cached.has_key (about)
                                ]
                except:
                        self.loginfo_traceback ()
                        return ()
                
                assert None == self.log (
                        'load filename="%s" id="%x"' % (
                                filename, id (module)
                                ), 'debug'
                        )

                self.presto_cached.update (controllers)
                self.presto_modules[filename] = (module, controllers)
                return controllers

        def presto_unload (self, filename):
                "unload a named Python module"
                module, controllers = self.presto_modules.get (filename)
                if module == None:
                        return ()
                        
                assert None == self.log (
                        'unload filename="%s" id="%x"' % (
                                filename, id (module)
                                ), 'debug'
                        )
                for about, controller in controllers:
                        del self.presto_cached[about]
                del self.presto_modules[filename]
                return controllers
        
        def http_continue (self, http):
                uri = http.request[1]
                try:
                        uri = list (HTTP_URI.match (uri).groups ())
                except:
                        uri = ['http://', http.collector_headers.get (
                                'host', self.presto_path
                                ), uri, '', '']
                else:
                        uri[0] = uri[0] or 'http://'
                        uri[1] = uri[1] or http.collector_headers.get (
                                'host', self.presto_path
                                )
                http.uri = uri
                about = uri[2].split ('/', 2)
                about[0] = uri[1]
                about = http.uri_about = tuple ((
                        unicode (urldecode (n), 'UTF-8') for n in about
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
                                controller = http_404_close

                try:
                        stalled = controller (http, about)
                except:
                        self.loginfo_traceback ()
                        http (500)
                        stalled = False
                try:
                        digest = http.irtd2[4]
                except:
                        digest = '%x' % id (http)
                loginfo.log (str (netstring.encode ((
                        ' '.join (http.request),
                        ''.join (uri[:3]),
                        digest
                        ))), '%d' % http.response)
                return stalled
        
"""
What PRESTo provides over Allegra's bare http_server API is one obvious way
to do Web 2.0 applications right, as simply as practically possible.
        
With three request methods:
        
    HEAD, GET and POST

Only two responses:
        
    200 Ok ... transfer a state/resources
    302 Redirect ... transfer *to* a state/resource

No other errors than the client's protocol failure (400, 401, 404, 405) or
the controllers unhandled exceptions (500).

And, last but not least, triple for resource locators:
        
    http://context/subject/predicate

Because flat is better than nested ;-)

    http://host/control
    http://host/control?...
    http://host/control/
    http://host/control/?...
    http://host/control/resource
    http://host/control/application?...

root/
        127.0.0.2/
                resource
                application?...
                control/
                        ?...
                        resource
                        application?...

A controller "control" access to resources, static and dynamic. 

The static resources are text representation of the application invariant 
state (the style sheets, the localized text, the JavaScript interactions, 
etc ...), they are cached in-memory every time the controller that depends
upon them is loaded.

Dynamic resources are the result of functions applied by the controller
to variable resources of the application: databases on the server side, 
AJAX display in the browser ... or just the peer state held by PRESTo.

"""