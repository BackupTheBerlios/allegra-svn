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

import types, glob, os, imp, weakref, time

from xml.parsers import expat

if os.name == 'nt':
        allegra_time = time.clock
else:
        allegra_time = time.time

from allegra import \
        loginfo, finalization, synchronizer, \
        producer, reactor, xml_dom, xml_unicode


# Asynchronous components

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


def true ():
        return True

def false ():
        return False

class Stalled_producer (object):
        
        def more (self):
                return ''
        
        producer_stalled = true
        
        def __call__ (self):
                self.producer_stalled = false


def presto_rollback (self, reactor):
        react = Stalled_producer ()
        reactor.presto_dom.presto_rollback ((react, ()))
        return react
                        
def presto_commit (self, reactor):
        react = Stalled_producer ()
        if reactor.presto_dom.presto_commit ((react, ())):
                return react
                        
class PRESTo_async (
        loginfo.Loginfo, finalization.Finalization, xml_dom.XML_element
        ):
                
        def __repr__ (self):
                return '%s id="%x"' % (
                        self.xml_name.encode ('UTF-8', 'ignore'), id (self)
                        )

        def finalization (self, instance):
                assert None == self.log ('finalized', 'debug')

        xml_name = u'http://presto/ async'

        presto_interfaces = set ((u'presto-host', u'presto-path'))
        
        def presto (self, reactor):
                assert None == self.log (
                        '%r' % reactor.presto_vector, 'presto'
                        )

        presto_methods = {
                u'rollback': presto_rollback,
                u'commit': presto_commit
                }
        

# Synchronized Component

class PRESTo_reactor_sync (reactor.Buffer_reactor):
        
        def __init__ (self, select_trigger):
                self.select_trigger = select_trigger
                reactor.Buffer_reactor.__init__ (self)
                
        def __call__ (self, data):
                assert type (data) == types.StringType
                self.select_trigger ((self.buffer, (data,)))


class PRESTo_sync (PRESTo_async, finalization.Finalization):

        xml_name = u'http://presto/ sync'
        
        __init__ = synchronizer.synchronized

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
        def synchronized (self, reactor):
                xml_reactor = PRESTo_reactor_sync (self.select_trigger)
                xml_reactor.presto_vector = reactor.presto_vector.copy ()
                self.synchronized ((method, (self, xml_reactor)))
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
                        self.xml_error = error
                        self.xml_parse_error ()
                        self.synchronized ((self.sync_close, ('re', )))
                else:
                        self.synchronized ((self.sync_read, ()))
                
        def async_close (self, mode):
                if mode[0] == 'r':
                        if mode[-1] == 'e':
                                try:
                                        self.xml_expat.Parse ('', 1)
                                except expat.ExpatError, error:
                                        self.xml_error = error
                                        self.xml_parse_error ()
                        self.xml_expat = self.xml_parsed = None
                        if self.xml_root == None:
                                self.xml_root = presto.PRESTo_async ()
                        if self.xml_root.xml_attributes == None:
                                self.xml_root.xml_attributes = {}
                for call, args in self.presto_defered:
                        call (*args)
                self.presto_defered = None
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
                        if type (self.presto_defered) == list:
                                self.presto_defered.append (defered)
                                return True
                        
                        return False
                
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
                
class PRESTo_root (loginfo.Loginfo):
        
        def __init__ (self, path):
                self.presto_path = path
                self.presto_types = {}
                self.presto_type = PRESTo_async
                self.presto_cached = {}
                self.presto_modules = {}
                for filename in self.presto_modules_dir ():
                        self.presto_module_load (filename)
                for filename in glob.glob (self.presto_path + '/*.xml'):
                        dom = PRESTo_dom (
                                filename, self.presto_types, self.presto_type
                                )
                        path = '/' + os.path.basename (filename)
                        self.presto_cached[path] = weakref.ref (dom)
                        dom.presto_path = path
                        dom.presto_root = self
                        dom.presto_rollback ((none, ()))
                
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
                        self.presto_path + '/*.py'
                        )]

        def presto_module_load (self, filename):
                if self.presto_modules.has_key (filename):
                        self.presto_module_unload (filename)
                name, ext = os.path.splitext (filename)
                try:
                        presto_module = imp.load_source (
                                name , self.presto_path + '/' + filename
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
        
        def presto_dom (self, reactor):
                # Check for a reference in the root's cache for that path or 
                # for a folder that contains it and if there is one, try to 
                # dereference the DOM instance, and return True if the method 
                # succeeded to attribute such instance to the reactor.
                #
                assert reactor.presto_path.startswith ('/')
                dom = self.presto_cached.get (reactor.presto_path, none) ()
                if dom != None:
                        reactor.presto_dom = dom
                        return True
                
                if self.PRESTo_FOLDER_DEPTH > 0:
                        depth = 0
                        path = reactor.presto_path.rsplit ('/', 1)[0]
                        while True:
                                dom = self.presto_cached.get (path, none) ()
                                if dom:
                                        reactor.presto_dom = dom
                                        return True
                                
                                depth += 1
                                if path and depth < self.PRESTo_FOLDER_DEPTH:
                                        path = path.rsplit ('/', 1)[0]
                                else:
                                        break
                                
                return False
        
        def presto_cache (self, reactor, filename):
                # instanciate a DOM, cache its weak reference, roll it back
                # and defer the PRESTo continuation ...
                #
                reactor.presto_dom = dom = PRESTo_dom (
                        filename, self.presto_types, self.presto_type
                        )
                self.presto_cached[reactor.presto_path] = weakref.ref (dom)
                dom.presto_path = reactor.presto_path
                dom.presto_root = self
                dom.presto_rollback ((
                        self.presto_continue, (reactor, )
                        ))
                assert None == self.log (
                        'cached count="%d"' % len (self.presto_cached), 
                        'debug'
                        )

        def presto_continue (self, reactor):
                assert None == self.log ('%r' % reactor, 'presto')
                

class PRESTo_benchmark (object):
        
        def __init__ (self, t):
                self.presto_request_time = t 
                self.presto_benchmark = allegra_time () - t
        
        def more (self):
                if self.presto_request_time == None:
                        return ''
                        
                t = allegra_time () - self.presto_request_time
                self.presto_request_time = None
                return (
                        '<!-- it took PRESTo %f seconds'
                        ' to handle this request and %f seconds'
                        ' to deliver this response -->' % (
                                self.presto_benchmark, 
                                t - self.presto_benchmark
                                )
                        )
                        
        def producer_stalled (self):
                return False


def presto_producer (
        reactor, encoding='ASCII', benchmark=None, globbing=512
        ):
        # return one single Composite_producer with a simplistic PRESTo
        # envelope made of two elements: the accessed DOM root and the 
        # byte string, unicode string, xml element or producer returned by
        # a call to presto_rest.
        #
        dom = reactor.presto_dom
        prefixes = dom.xml_prefixes
        e = xml_dom.XML_element ()
        e.xml_name = u'http://presto/ PRESTo'
        e.xml_attributes = reactor.presto_vector
        e.xml_children = [reactor.presto_rest, dom.xml_root]
        if benchmark != None:
                e.xml_children.append (PRESTo_benchmark (benchmark))
        head = '<?xml version="1.0" encoding="%s"?>' % encoding
        if reactor.presto_dom.xml_pi:
                head += xml_unicode.xml_pi (dom.xml_pi, encoding)
        return producer.Composite_producer (
                head, xml_unicode.xml_prefixed (
                        e, prefixes, xml_unicode.xml_ns (prefixes), encoding
                        ), globbing
                )


# the core PRESTo interface/implementation itself, just REST
                
def presto_rest (reactor, handler):
        # 0. test for a PRESTo_element
        #
        xml_root = reactor.presto_dom.xml_root
        if not hasattr (xml_root, 'presto_interfaces'):
                # 1a. Simply produce the XML ... possibly aggregating 
                # asynchronous and synchronous data flows
                #
                return '<presto:presto xmlns:presto="http://presto/" />'
                
        # 1b. mask the REST vector or XML attributes with the PRESTo
        #     interfaces, providing one copy of what could become the
        #     the state of the xml_root instance interface.
        #
        #     also, make a set of this "masked" state interfaces and
        #     attach both to the reactor ...
        #
        #     the purpose of this implementation is to filter out undefined
        #     interfaces, complete the REST vector with XML attributes
        #     values (if they are available), and provide PRESTo methods
        #     with an independant copy of the method/instance REST state
        #     that those methods can manipulate without conflicts and
        #     which carries a practical interaction state for both the
        #     browser and peer.
        #
        reactor.presto_interfaces = set (
                reactor.presto_vector.keys ()
                ).intersection (xml_root.presto_interfaces)
        if xml_root.xml_attributes:
                xml_interfaces = xml_root.presto_interfaces.union (
                        set (xml_root.xml_attributes.keys ())
                        )
                reactor.presto_vector = dict ([
                        (k, xml_root.xml_attributes.get (k, u''))
                        for k in xml_interfaces.difference (
                                reactor.presto_interfaces
                                )
                        ]+[
                        (k, reactor.presto_vector[k])
                        for k in reactor.presto_interfaces
                        ])
        else:
                reactor.presto_vector = dict ([
                        (k, reactor.presto_vector[k])
                        for k in reactor.presto_interfaces
                        ])
        #
        # 2. Invoke the method named, the default "presto" or none
        #
        if (
                ('PRESTo' in reactor.presto_interfaces) and
                xml_root.presto_methods.has_key (
                        reactor.presto_vector['PRESTo']
                        )
                ):
                # 2a. try to invoke the method specified by the PRESTo
                #     interface and declared by the instance's presto_methods
                #
                try:
                        result = xml_root.presto_methods[
                                reactor.presto_vector['PRESTo']
                                ] (xml_root, reactor)
                except:
                        # log traceback via the handler, do not require
                        # a logging facility from the instance accessed
                        # but instead log the exception to the accessor.
                        #
                        return (
                                '<presto:excp'
                                ' xmlns:presto="http://presto/"'
                                ' >%s</presto:excp>' % presto_xml (
                                        handler.loginfo_traceback (), set ()
                                        )
                                )

        else:
                # 2b. try to invoke the "default" instance method 'presto'
                #
                try:
                        result = xml_root.presto (reactor)
                except Exception, error:
                        # log traceback via the handler
                        return (
                                '<presto:excp'
                                ' xmlns:presto="http://presto/"'
                                ' >%s</presto:excp>' % presto_xml (
                                        handler.loginfo_traceback (), set ()
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
        types.DictProxyType, # what's this?
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
        types.XRangeType, # and this?
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
                return '<str%s repr="%s">%s</str>' % (
                        attributes, 
                        xml_unicode.xml_attr (
                                unicode ('%r' % instance), encoding
                                ),
                        xml_unicode.xml_cdata (unicode (instance), encoding)
                        )

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
                pass
        # 5. try to serialize as an 8-bit string, using the default encoding
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
#
# Allegra PRESTo is unRESTricted
#
# You may as well handle HTTP yourself, set the HTTP response's MIME body 
# to a simple XML producer like:
#
#         def presto (self, reactor):
#                reactor.mime_producer_body = producer.Simple_producer (
#                        '<pizza-order>...</pizza-order>'
#                        )
#
# if you prefer to provide only the REST state to your client. Developpers
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