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

"Practical REST objects"

import types, glob, os, imp, weakref, time

from xml.parsers import expat

if os.name == 'nt':
        allegra_time = time.clock
else:
        allegra_time = time.time

from allegra import \
        loginfo, finalization, synchronizer, \
        producer, reactor, xml_dom, xml_unicode


# TODO: move away ...

class PRESTo_reactor (reactor.Buffer_reactor):
        
        def __init__ (
                self, react, response='<presto xmlns="http://presto/" />'
                ):
                reactor.Buffer_reactor.__init__ (self)
                self.presto_react = react
                self.presto_response = response
        
        def __call__ (self, *args):
                self.presto_react (*args)
                self.presto_react = None
                self.buffer (self.presto_response)
                self.buffer ('') # ... buffer_react ()


class PRESTo_async (
        loginfo.Loginfo, finalization.Finalization, xml_dom.XML_element
        ):
                
        "The base PRESTo component class."
        
        def __repr__ (self):
                return '%s id="%x"' % (self.xml_name.encode (
                        'UTF-8', 'xmlcharrefreplace'
                        ), id (self))

        def finalization (self, instance):
                assert None == self.log ('finalized', 'debug')

        xml_name = u'http://presto/ async'

        def presto (self, reactor):
                assert None == self.log ('%r' % reactor, 'presto')

        presto_methods = {}
        presto_interfaces = set ()
        

# Synchronized Component

class PRESTo_reactor_sync (reactor.Buffer_reactor):
        
        def __init__ (self, select_trigger):
                self.select_trigger = select_trigger
                reactor.Buffer_reactor.__init__ (self)
                
        def __call__ (self, data):
                assert type (data) == types.StringType
                self.select_trigger ((self.buffer, (data,)))


class PRESTo_sync (PRESTo_async):

        "A derived generic component to synchronize threaded methods."

        xml_name = u'http://presto/ sync'
        
        synchronizer = None
        synchronizer_size = 16
        
        def __init__ (self, name, attributes):
                xml_dom.XML_element.__init__ (self, name, attributes)
                synchronizer.synchronized (self)
        
        # Note also that there are two logging interfaces for a synchronized
        # PRESTo instance, asynchronous and synchronous:
        #
        #       self.log ('async')
        #
        # and
        #
        #       self.synchronizer.log ('sync')
        #

        # The idea is to pass a distinct copy of the asynchronous state and
        # allow the synchronized method to access it safely.
        #
        # Synchronized method must not update the XML tree or any
        # asynchronously managed data structures, but they are expected to
        # access at least the most relevant state: its request's state, the
        # PRESTo vector. Such method will access the instance bound to,
        # but with utmost care and certainly not its xml_* or presto_*
        # interfaces.
        #
        # A synchronized method is guaranteed to be "thread-safe" if it does
        # not access anything else than the synchronized reactor passed as
        # argument.
        #
        # Most "real-world" implementation should validate all requests
        # asynchronously and then eventually invoke synchronized methods.

        
def presto_synchronize (method):
        def synchronized (element, reactor):
                xml_reactor = PRESTo_reactor_sync (element.select_trigger)
                xml_reactor.presto_vector = reactor.presto_vector.copy ()
                element.synchronized ((method, (element, xml_reactor)))
                return xml_reactor
                
        return synchronized
        #
        # a method factory that "wraps" the asynchronous PRESTo reactor 
        # handled with a synchronized buffer reactor before passing it
        # to the "decorated" method.


# A Synchronized XML document loader, reading and writing a file to a 
# synchronous and threaded file descriptor, but parsing and serializing
# the XML string asynchronously. This is a crude form of non-blocking
# persistence for PRESTo, to and from the filesystem. It serves as a base
# class to derive threaded BSDDB persistence and asynchronous PNS/TCP
# layers.
#
# Flat Is Better Than Nested (from "The Zen of Python")
#
# This is a typical Allegra class, with a relatively large namespace, not
# an instance tree. The practical reason is that Python instanciation is
# significantly expensive (it's 50 times slower than C++, Lisp, etc!).
#
# A Single Namespace Is Better Than Many (The Zen of Allegra)
#
# This impose a strict requirement on attribute names, which anyway
# is "The Right Thing To Do": a clean non-conflicting namespace for the
# library and application. Names like "parent", "parse" or "read" are 
# forbidden, because they are not articulated enough, possibly semantically
# dispersed and therefore prohibiting flatter instance trees.

class PRESTo_dom (
        xml_dom.XML_dom, loginfo.Loginfo, finalization.Finalization
        ):
        
        synchronizer = None
        synchronizer_size = 4
        #
        # let a blocking I/O stall no more than one DOM out of 4, ymmv.
        
        sync_buffer = 4096
        
        presto_defered = None
        
        def __init__ (self, name, types={}, type=PRESTo_async):
                self.xml_prefixes = {u'http://presto/': u'presto'}
                self.xml_pi = {}
                self.xml_type = type
                self.xml_types = types
                self.presto_name = name
                synchronizer.synchronized (self)
                        
        def __repr__ (self):
                return 'presto-dom name="%s"' % self.presto_name
                        
        def async_open (self, mode):
                if mode[0] == 'r':
                        self.xml_parser_reset ()
                        self.synchronized ((self.sync_read, ()))
                elif mode[0] == 'w':
                        self.synchronized ((self.sync_write, (
                                xml_unicode.xml_string (self.xml_root, self),
                                )))
                        self.synchronized ((self.sync_close, ('w', )))

        def async_read (self, data):
                try:
                        self.xml_expat.Parse (data, 0)
                except expat.ExpatError, error:
                        self.xml_expat_ERROR (error)
                        self.synchronized ((self.sync_close, ('re', )))
                else:
                        self.synchronized ((self.sync_read, ()))
                
        def async_close (self, mode):
                if mode[0] == 'r':
                        if mode[-1] == 'e':
                                try:
                                        self.xml_expat.Parse ('', 1)
                                except expat.ExpatError, error:
                                        self.xml_expat_ERROR (error)
                        self.xml_expat = self.xml_parsed = None
                        if self.xml_root == None:
                                self.xml_root = PRESTo_async (
                                        u'http://presto/ async', None
                                        )
                        if self.xml_root.xml_attributes == None:
                                self.xml_root.xml_attributes = {}
                defered = self.presto_defered
                self.presto_defered = None
                for call, args in defered:
                        call (*args)
                #
                # defered continuations are queued nicely and called
                # in sequence, asynchronously. this means that concurrent
                # access to a persistent component instance is done without
                # errors: ten requests to a "loading" instance will be
                # handled asynchronously once the instance is loaded but
                # only the first request will force the cache to access the
                # original resource, parse the XML document and instanciate
                # the component DOM.

        # The PRESTo commit and rollback interfaces
        
        def presto_rollback (self, defered):
                if self.presto_defered:
                        try:
                                self.presto_defered.append (defered)
                        except:
                                return False
                                #
                                # you can't roll it back while it's
                                # committing, anyway it would be useless
                                # to do so ...
                        
                else:
                        self.presto_defered = [defered]
                        self.xml_root = None
                        self.synchronized ((
                                self.sync_open, (self.presto_name, 'r')
                                ))
                return True
        
        def presto_commit (self, defered):
                if self.presto_defered:
                        return False
                
                self.presto_defered = (defered, )
                self.synchronized ((
                        self.sync_open, (self.presto_name, 'w')
                        ))
                return True
        
PRESTo_dom.sync_open = synchronizer.sync_open
PRESTo_dom.sync_write = synchronizer.sync_write
PRESTo_dom.sync_read = synchronizer.sync_read
PRESTo_dom.sync_close = synchronizer.sync_close


# Loading and unloading Python modules, XML namespace to types mapping.
                
def none (): pass
                
PASS = (none, ())
                
class PRESTo_root (loginfo.Loginfo):
        
        presto_type = PRESTo_async
        
        def __init__ (self, path):
                self.presto_path = path + '/root'
                self.presto_path_python = path + '/modules'
                self.presto_types = {}
                self.presto_cached = {}
                self.presto_modules = {}
                for filename in self.presto_modules_dir ():
                        self.presto_module_load (filename)
                for filename in glob.glob (self.presto_path + '/*'):
                        self.presto_cache (
                                '/' + os.path.basename (filename), PASS
                                )
                        
        def __repr__ (self):
                return 'presto-root path="%s"' % self.presto_path

        # What's *specially* nice with the asynchronous design is that Python
        # modules reload is both efficient (reloading an identical module is
        # as fast as checking source identity, apparently ;-) and safe. Indeed
        # loading a new module *will* block the peer until it is compiled,
        # but doing it in a thread is just planning failure. Think about why
        # you would reload a module in a web application peer: debug during
        # development or maintenance of a production run. When developing 
        # performance does not matter. And it certainly does matter a lot less
        # than stability when maintaining a runtime environnement!
        #
        # Asynchronous is as fast as a safe network peer can get ;-)
        
        def presto_modules_dir (self):
                return [os.path.basename (n) for n in glob.glob (
                        self.presto_path_python + '/*.py'
                        )]

        def presto_module_load (self, filename):
                if self.presto_modules.has_key (filename):
                        self.presto_module_unload (filename)
                name, ext = os.path.splitext (filename)
                try:
                        presto_module = imp.load_source (
                                name , '/'.join ((
                                        self.presto_path_python, filename
                                        ))
                                )
                        if (
                                self.presto_modules.has_key (filename) and 
                                hasattr (presto_module, 'presto_onload')
                                ):
                                presto_module.presto_onload (self)
                except:
                        self.loginfo_traceback ()
                        return
        
                # update this PRESTo root XML namespace to classes mapping
                # with any module's name that has an 'xml_name' attribute.
                #
                assert None == self.log (
                        'load-module filename="%s" id="%x"' % (
                                filename, id (presto_module)
                                ), 'debug'
                        )
                self.presto_modules[filename] = presto_module
                if not hasattr (presto_module, 'presto_components'):
                        presto_module.presto_components = ()
                self.presto_types.update (dict ([
                        (item.xml_name, item)
                        for item in presto_module.presto_components
                        ]))

        def presto_module_unload (self, filename):
                presto_module = self.presto_modules.get (filename)
                if presto_module == None:
                        return
                        
                assert None == self.log (
                        'unload-module filename="%s" id="%x"' % (
                                filename, id (presto_module)
                                ), 'debug'
                        )
                for item in presto_module.presto_components:
                        del self.presto_types[item.xml_name]
                del self.presto_modules[filename]
        
        # In order to limit the possible damage of broken/malicious
        # URLs, a strict depth limit of 2 is set by default, just enough
        # to support a "/model/control/view" syntax ...
        #
        PRESTo_FOLDER_DEPTH = 2
        
        def presto_route (self, reactor):
                # Check for a reference in the root's cache for that path or 
                # for a folder that contains it and if there is one, try to 
                # dereference the DOM instance, and return True if the method 
                # succeeded to attribute such instance to the reactor.
                #
                try:
                        dom = self.presto_cached[reactor.presto_path] ()
                except KeyError:
                        pass
                else:
                        if dom != None:
                                reactor.presto_dom = dom
                                return True
                
                if self.PRESTo_FOLDER_DEPTH > 0:
                        depth = 0
                        path = reactor.presto_path.rsplit ('/', 1)[0]
                        while True:
                                try:
                                        dom = self.presto_cached[path] ()
                                except KeyError:
                                        pass
                                else:
                                        if dom != None:
                                                reactor.presto_dom = dom
                                                return True
                                        
                                depth += 1
                                if path and depth < self.PRESTo_FOLDER_DEPTH:
                                        path = path.rsplit ('/', 1)[0]
                                else:
                                        break
                                
                return False
        
        def presto_dom (self, reactor):
                try:
                        dom = self.presto_cached[reactor.presto_path] ()
                except KeyError:
                        dom = None
                if dom == None:
                        reactor.presto_dom = self.presto_cache (
                                reactor.presto_path, (
                                        self.presto_continue, (reactor, )
                                        )
                                )
                else:
                        reactor.presto_dom = dom
                        self.presto_continue (reactor)
                
        def presto_cache (self, path, rolledback=PASS):
                # instanciate a DOM, cache its weak reference, roll it back
                # and defer the PRESTo continuation ...
                #
                dom = PRESTo_dom (
                        self.presto_path + path, 
                        self.presto_types, 
                        self.presto_type
                        )
                self.presto_cached[path] = weakref.ref (dom)
                dom.presto_path = path
                dom.presto_root = self
                dom.presto_rollback (rolledback)
                assert None == self.log (
                        'cached count="%d"' % len (self.presto_cached), 
                        'debug'
                        )
                return dom

        def presto_continue (self, reactor):
                assert None == self.log ('%r' % reactor, 'presto')
                

def presto_producer (
        dom, attributes, result, encoding, globbing=512
        ):
        # return one single Composite_producer with a simplistic PRESTo
        # envelope made of two elements: the accessed DOM root and the 
        # byte string, unicode string, xml element or producer returned by
        # a call to presto_rest.
        #
        prefixes = dom.xml_prefixes
        e = xml_dom.XML_element (u'http://presto/ PRESTo', attributes)
        e.xml_children = (result, dom.xml_root)
        head = '<?xml version="1.0" encoding="%s"?>' % encoding
        if dom.xml_pi:
                head += xml_unicode.xml_pi (dom.xml_pi, encoding)
        return producer.Composite_producer (
                head, xml_unicode.xml_prefixed (
                        e, prefixes, xml_unicode.xml_ns (prefixes), encoding
                        ), globbing
                )


class PRESTo_benchmark (object):
        
        def __init__ (self, t):
                self.response_time = allegra_time () - t
                self.request_time = t 
        
        def more (self):
                if self.request_time == None:
                        return ''
                        
                t = allegra_time () - self.request_time
                self.request_time = None
                return (
                        '<!-- it took PRESTo %f seconds'
                        ' to handle this request and %f seconds'
                        ' to deliver this response -->' % (
                                self.response_time, 
                                t - self.response_time
                                )
                        )
                        
        def producer_stalled (self):
                return False


def presto_benchmark (
        dom, attributes, result, encoding, benchmark, globbing=512
        ):
        # return one single Composite_producer with a simplistic PRESTo
        # envelope made of two elements: the accessed DOM root and the 
        # byte string, unicode string, xml element or producer returned by
        # a call to presto_rest.
        #
        prefixes = dom.xml_prefixes
        e = xml_dom.XML_element (
                u'http://presto/ PRESTo', attributes
                )
        e.xml_children = (result, dom.xml_root, benchmark)
        head = '<?xml version="1.0" encoding="%s"?>' % encoding
        if dom.xml_pi:
                head += xml_unicode.xml_pi (dom.xml_pi, encoding)
        return producer.Composite_producer (
                head, xml_unicode.xml_prefixed (
                        e, prefixes, xml_unicode.xml_ns (prefixes), encoding
                        ), globbing
                )


# the core PRESTo interfaces/implementation itself, just REST

# Types with safe __str__ 

PRESTo_String = (
        # Ordered most common first
        types.StringType, 
        types.IntType,
        types.LongType,
        types.FloatType,
        types.BooleanType,
        types.NoneType,
        )

# Types with safe __iter__ 

PRESTo_Iterable = (types.TupleType, types.ListType, set, frozenset)

#
# TODO: ... find out more about the types below
#

PRESTo_others = (
        types.InstanceType,
        types.ObjectType,
        types.ClassType,
        types.TypeType,
        types.CodeType, 
        types.UnboundMethodType,
        types.BuiltinMethodType,
        types.NotImplementedType,
        types.BuiltinFunctionType,
        types.DictProxyType,
        types.MethodType,
        types.GeneratorType,
        types.EllipsisType,
        types.ModuleType,
        types.FrameType,
        types.FileType,
        types.BufferType,
        types.TracebackType,
        types.SliceType,
        types.ComplexType,
        types.LambdaType,
        types.FunctionType,
        types.XRangeType,
        )

def presto_xml (
        instance, walked,
        attributes=' xmlns="http://presto/"', horizon=1024, encoding='ASCII',
        ):
        # Serialize any Python state to an XML string, using by default
        # an charset encoding that is supported everywhere: 7bit ASCII.
        #
        # A PRESTo state is a tree of "simple" instances, like a list
        # of strings or a map of unicode and sets, etc ...
        #
        # It is what a Python function is supposed to return, a method
        # to update but that in the end will be pushed out, not serialized
        # back to persistence. This implementation is recursive: if you
        # need to dump a long list of instance to XML, it may be actually
        # simpler to join some ad-hoc formatted XML strings.
        #
        t = type (instance)
        attributes += ' type="%s"' % xml_unicode.xml_attr (
                unicode (t.__name__), encoding
                )
        if issubclass (t, PRESTo_String):
                # 1. Byte string
                #return '<str%s repr="%s">%s</str>' % (
                #        attributes, 
                #        xml_unicode.xml_attr (
                #                unicode ('%r' % instance), encoding
                #                ),
                #        xml_unicode.xml_cdata (unicode (instance), encoding)
                #        )
                #
                return '<str%s><![CDATA[%s]]></str>' % (attributes, instance)

        elif issubclass (t, types.UnicodeType):
                # 2. UNICODE string
                return '<str%s>%s</str>' % (
                        attributes, xml_unicode.xml_cdata (instance, encoding)
                        )

        instance_id = id (instance)
        if isinstance (instance, PRESTo_Iterable) and not instance_id in walked:
                # 3. simple iterables: tuple, list, etc ...
                walked.add (instance_id)
                if len (walked) > horizon:
                        attributes += ' horizon="%d"' % horizon
                else:
                        return '<iter%s>%s</iter>' % (
                                attributes, 
                                ''.join ([
                                        presto_xml (
                                                i, walked, '',
                                                horizon, encoding
                                                )
                                        for i in instance
                                        if not id (i) in walked
                                        ])
                                )
        
        elif isinstance (instance, dict) and not instance_id in walked:
                walked.add (instance_id)
                if len (walked) > horizon:
                        attributes += ' horizon="%d"' % horizon
                else:
                        # 4. dictionnary
                        items = [(
                                presto_xml (
                                        k, walked, '',
                                        horizon, encoding
                                        ),
                                presto_xml (
                                        v, walked, '',
                                        horizon, encoding
                                        )
                                ) for k, v in instance.items ()]
                        return '<map%s>%s</map>' % (
                                attributes,
                                ''.join ([
                                        '<item>%s%s</item>' % i
                                        for i in items if i[0] or i[1]
                                        ])
                                )
                                        
        if instance_id in walked:
                return '<str%s>...</str>' % attributes
                
        # 4. try to serialize as an 8-bit "representation"
        try:
                attributes += ' repr="%s"' % xml_unicode.xml_attr (
                        u'%r' % instance, encoding
                        )
        except:
                # 5. try to serialize as an 8-bit string, using the default 
                #    encoding ...
                #
                try:
                        return '<str%s>%s</str>' % (
                                attributes, xml_unicode.xml_cdata (
                                        unicode ('%s' % instance), encoding
                                        )
                                )
                                
                except:
                        pass

        # 6. all other interfaces/types
        return '<instance%s/>' % attributes


def presto_rest (method, component, reactor):
        try:
                result = method (component, reactor)
        except:
                # log traceback via the handler
                return (
                        '<presto:excp'
                        ' xmlns:presto="http://presto/"'
                        ' >%s</presto:excp>' % presto_xml (
                                loginfo.loginfo_traceback (), set ()
                                )
                        )
                                
        # return <presto/> for None (the "default" continuation)
        if result == None:
                return '<presto:presto xmlns:presto="http://presto/" />'
                
        if (
                type (result) in types.StringTypes or 
                hasattr (result, 'more') or 
                hasattr (result, 'xml_name')
                ):
                # UNICODE, byte string, producer or XML element, ...
                return result
                
        # others types and interfaces.
        return presto_xml (result, set ())


# Practical method dispatcher and REST routing to a named XML element in the 
# component's tree. This is just enough to emulate safely state acquisition,
# provide easy-to-forward-cache RESTfull application interfaces, and does
# not restrict more purposefull handlers.

def presto_method (component, reactor):
        "dispatch the REST request to one of the PRESTo methods"
        method = component.presto_methods.get (unicode (
                reactor.presto_path[:len (
                        component.xml_dom.presto_path
                        )], 'UTF-8'
                ))
        if method != None:
                return method (component, reactor)


def presto_route (component, reactor):
        "maybe route the REST request further, or dispatch a PRESTo method"
        route = reactor.presto_path[:len (component.xml_dom.presto_path)]
        element = component.presto_routes.get (route)
        if element != None:
                return element.presto (reactor)
                
        method = component.presto_methods.get (unicode (route, 'UTF-8'))
        if method != None:
                return method (component, reactor)


def presto_route_set (element, dom):
        "instanciate or update the component's REST routing table"
        if element.xml_parent != None:
                dom.xml_root.presto_routes[element.xml_attributes.get (
                        u'presto-route', xml_unicode.xml_tag (element.xml_name)
                        ).encode ('UTF-8', 'ignore')] = element
        #
        # note that elements and components do not worry about cleaning up
        # this routing table: such elements and components are not meant to
        # be updated in part but in whole.

        
# Note about this implementation
#
# PRESTo towers at the top of Allegra's semantic web stack, providing
# one obvious way to develop distributed web applications. It integrates
# Allegra's asynchronous core, synchronization and XML model into one
# network application component interface (and implementation).
#
# This module packs together a simple REST interface for XML component
# instances rolled-back and committed synchronously to the file system.
# It provides PRESTo's HTTP server with the simplest implementation of the
# XML component meme found in many web development framework (see 
# presto_http.py).
#
# Remarkably, its interfaces also support persistence provided by
# synchronized BSDDB databases and distributed PNS metabases (see 
# presto_bsddb.py and presto_pns.py).
#
# Also, PRESTo comes with a practical middle-ground between simplistic 
# REST implementations and SOAP's over-engineered specifications. Enough
# to develop web user interface with stateless XML transformation only.
#
# Finally, PRESTo is not restricted to HTTP and can be applied to other
# MIME or message queue protocols (like SMTP, QMQP, etc ...). PRESTo will
# not be completed until a reference implementation for another protocol
# than HTTP has been tested with an application (preferably QMQP).
#
#
# Examples
#
# For instance, the XML document
#
#         <async xmlns="http://presto/"/>
#
# saved as
#
#        ./instance.xml
#
# can be rolled-back and commited synchronously by a PRESTo_cache as an
# instance of the class PRESTo_async, provided that the following module 
# was loaded by this cache:
#
#        from allegra import presto
#        presto_components = (prest.PRESTo_async, )
#
# Dispatched this cache, the HTTP request:
#
#        GET http://127.0.0.1/instance.xml HTTP/1.1
#        Host: 127.0.0.1
#        ...
#
# yields an HTTP response with a simple XML body:
#
#        HTTP/1.1 200 Ok
#        ...
#
#        <?xml version="1.0" encoding="ASCII"?>
#        <PRESTo xmlns="http://presto/"
#                host="127.0.0.1" path="/instance.xml"
#                >
#                <presto/>
#                <async/>
#        </PRESTo>
#
# and provides just enough states to conduct an transaction over a stateless
# protocol like HTTP: the REST, method and the instance states. Those three
# states are practically enough to develop asynchronous web interfaces for
# statefull instances, using stateless XML transformations only (be it XSLT
# CSS or JavaScript).
#
# Here is another example, the infamous HelloWorld for PRESTo:
#
#        1. Python Module
#
#        from allegra import presto_http
#        class HelloWorld (presto_http.get_form):
#                xml_name = u'HelloWorld'
#                def helloworld (self, reactor):
#                        return u'Hello %s' % reactor.presto_vector[u'name']
#                presto_methods = {None: helloworld}
#                presto_interfaces = ((u'name', ))
#
#        2. XML file
#
#        <HelloWorld/>
#
#        3. HTTP request and REST response:
#
#        GET http://127.0.0.1/HelloWorld.xml?name=You HTTP/1.1
#        Host: 127.0.0.1
#        ...
#
#        HTTP/1.1 200 Ok
#        ...
#
#        <?xml version="1.0" encoding="ASCII"?>
#        <presto:PRESTo xmlns:presto="http://presto/"
#                presto-path="/HelloWorld.xml"
#                name="You"
#                >
#                Hello You
#                <HelloWorld/>
#        </presto:PRESTo>
#
#        with CRLF added in the XML response for better readability.
#
# Allegra PRESTo is unRESTricted
#
# You may as well handle HTTP yourself, set the HTTP response's MIME body 
# to a simple XML producer like:
#
#         def presto (self, reactor):
#                presto_http.rest (
#                        reactor, '<pizza-order>...</pizza-order>', 200
#                        )
#
# if you prefer to provide your flavor of REST to your client. Developpers
# of AJAX applications can also provide simple RPC producers and bypass
# serialization of all three PRESTo states (using XML/RPC, JSON, etc ...).
#
# Also, PRESTo can deliver "degraded" stateless interfaces for safe web 
# clients (without JavaScript I mean) and flicker-free AJAX interfaces, by 
# synchronizing all or parts of the server and client DOM.
#
#
# A Few States Only
#
# There are at least four and at most seven types of PRESTo states for each
# REST request:
#
# 1. a synchronized filesystem persitence root containing ...
# 2. a cached XML document object model holding ...
# 3. a PRESTo component instance which methods may return ...
# 4. an asynchronous or synchronized REST reactor, a producer,
#    a simple 8-bit string or any Python instance that can be
#    serialized safely with presto_xml () and be included in ...
# 5. an asynchronous XML producer
# 
# The first two PRESTo states listed above are cached, the third may be cached 
# too and the fourth and fifth may be replaced by a single response producer 
# state for methods that are specialized for a protocol. 
# 
# To those 4/5 states must be added the protocol states. Usually three for 
# HTTP/1.1: channel, request/response reactor and chunked producer wrapper, 
# maybe more depending on the kind of HTTP command and headers.
#
# I don't count the select_trigger, synchronizer, thread or queue states
# implied by synchronization since they are all cached or limited, using
# only more resources when they are available.
#
#
# High Performances
#
# HTTP request to cached PRESTo component instance need by default at most
# five states, but only four once pipelined through the same session. The
# result is sub-millisecond performance for simplistic REST call: 0.000527
# seconds on a 1.7Ghz Intel CPU under Windows XP Pro, from the request
# instanciation to the instanciation of a MIME producer body for the HTTP
# response. And that figure will still improve - possibly of one order of 
# magnitude - once all high-profile functions of Allegra have been optimized
# in a C module.
#
# All that power derives from a simple and consistent stack or well-
# articulated API that sticked to a practical and time-proven design
# for high-performance asynchronous network server.
#
#
# Blurb Mode On
#
# PRESTo is radically simple. 
#
# It is radically simpler than .NET or J2EE. It is also simpler than Rails, 
# Zope or your own flavor of LAMP, be it PHP or that good old Perl. 
#
# It's the One Obvious Way To Do It, the Python way.
#
# PRESTo is simpler to learn, simpler to apply and simpler to scale up.
#
# It is a web development jumpstart solution like Rails, but carrying all the
# experience of Python's asynchronous network development and bringing in a
# disruptive innovation. It provides web application developpers a functional
# equivalent of LAMP/J2EE/.NET host, reduced to Python and the simplest stack
# of standards common to all: MIME, HTTP, HTML, XML, XSLT, CSS and JavaScript. 
# PRESTo integrates a distributed resource resolution system (PNS) to enable 
# web application distribution on a peer network.
#
#
# Riding the Riddle of Asynchronicity
#
# This is what PRESTo makes possible and simple.
#
# 
#
#
# Simpler to learn
#
# PRESTo is simpler to understand because it extends the common stack of
# web standards in the simplest way possible to achieve the same effect 
# than mega-frameworks. 
#
# From logging and threading to distributed resource resolution, Allegra
# provides simpler protocols, simpler implementations and simpler APIs
# than its competitors. 

# PRESTo is simpler to learn because its sources are much shorther.
# With less than 50 modules and 20.000 lines or code and comments,
# Allegra - its supporting library - is a lot faster to skip through.
#
# Also, Allegra is written like a library, divided into relevant
# parts, each module and groups of modules preceding all the ones 
# that depend on it. Reading Allegra's API documentation, source
# code and manual will leave the same lasting understanding of the
# framework and most profitable knowledge, a practical one.
#
# Toying with Allegra's sources from the prompt is probably easier and
# more effective than trying to cope with the succint documentation
# of a verbose and proprietary API. A seasoned web developper will
# get actual experience of all Allegra's features in less time than 
# it takes to skip through its competitors documentation.
#
# Last but not least, PRESTo is simpler to learn because it does not
# try to reinvent the wheel and sticks to the stable stack of Web
# standards allready implemented in browsers, Python and its builtin
# C libraries.
#
#
# Simpler to apply
#
# PRESTo is simpler to apply because it provides a consistent and integrated
# implementation of a simpler stack of standards. If you have developped
# web applications, you know that it entails the integration of HTTP and
# HTML, but also JavaScript, CSS and now XML, XSLT and AJAX. The language
# use to develop the code of a web application may be PHP, Perl, Python,
# Java, C or C#, its host may be Apache, Microsoft IIS or a JBoss server,
# but it will be integrated to the same standard stack.
#
# PRESTo sticks to this standard stack, adding as less protocol and 
# specification as possible to implement statefullness, persistence and
# distribution, leaving the developpers the opportunity to articulate most
# of their application with that standard stack.
#
# As you will notice, PRESTo does not come with yet another markup language 
# of its own but instead rely exclusively on the client's ability to use
# JavaScript, XSLT or CSS stylesheets to display or otherwise handle the XML
# returned.
#
# Also, and that is almost a blaspheme, PRESTo does not come with yet another
# ORM or string of SQL connectors. Instead, this web framework rely on BSDDB
# for all its database applications and depends on a PNS metabase peer to
# develop distributed applications.
#
# Maybe as unorthodox, PRESTo comes with a simple XML component model for
# REST call to instance's method and the default persistence is to the
# file system, not some SQL server.
#
# By default, PRESTo produces XML documents that bundle the REST request's
# state, its response as well as the result state of the method's instance
# invoked. Also, by default, PRESTo serialize the invoked methods result
# in the most practical way for a stateless web client interface.
#
#
# Simpler to Scale Up
#
# At the bottom of PRESTo there is the integration into the PNS metabase
#
# The Allegra library integrates PRESTo and builds on its PNS reference
# implementation to deliver a simpler solution than SPREAD, JXTA and other
# distributed resource resolution systems. Thanks to PNS, PRESTo provides a
# simpler way to scale up web services but also a foundation to develop new 
# kind of metabase applications.
#
#