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
if os.name == 'nt':
        allegra_time = time.clock
else:
        allegra_time = time.time

from allegra.loginfo import Loginfo, compact_traceback
from allegra.finalization import Finalization
from allegra.producer import Composite_producer
from allegra.reactor import Buffer_reactor
from allegra.xml_dom import XML_dom, XML_element
from allegra.xml_unicode import \
        xml_attr, xml_cdata, xml_pi, xml_ns, xml_prefixed
from allegra.synchronizer import Synchronized

# First thing first, from Python state to XML string

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

PRESTo_Iterable = (types.TupleType, types.ListType, set)

#
# TODO: ... find out more about the types below
#
#types.InstanceType,
#types.ObjectType,
#types.ClassType,
#types.TypeType,
#types.CodeType, 
#types.UnboundMethodType,
#types.BuiltinMethodType,
#types.NotImplementedType,
#types.BuiltinFunctionType,
#types.DictProxyType, # what's this?
#types.MethodType,
#types.GeneratorType,
#types.EllipsisType,
#types.ModuleType,
#types.FrameType,
#types.FileType,
#types.BufferType,
#types.TracebackType,
#types.SliceType,
#types.ComplexType,
#types.LambdaType,
#types.FunctionType,
#types.XRangeType, # and this?

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
        attributes += ' type="%s"' % xml_attr (
                unicode (t.__name__), encoding
                )
        if issubclass (t, PRESTo_String):
                # 1. Byte string
                return '<str%s repr="%s">%s</str>' % (
                        attributes, 
                        xml_attr (unicode ('%r' % instance), encoding),
                        xml_cdata (unicode (instance), encoding)
                        )

        elif issubclass (t, types.UnicodeType):
                # 2. UNICODE string
                return '<str%s>%s</str>' % (
                        attributes, xml_cdata (instance, encoding)
                        )

        instance_id = id (instance)
        if issubclass (t, PRESTo_Iterable) and not instance_id in walked:
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
        
        elif issubclass (t, types.DictType) and not instance_id in walked:
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
                
        # 4. try to serialize as an 8bit "representation"
        try:
                attributes += ' repr="%s"' % xml_attr (
                        u'%r' % instance, encoding
                        )
        except:
                pass
        # 5. try to serialize as an 8bit string, using the default encoding
        try:
                return '<str%s>%s</str>' % (attributes, xml_cdata (
                        unicode ('%s' % instance), encoding
                        ))
                        
        except:
                pass

        # 6. all other interfaces/types
        return '<instance%s/>' % attributes


class PRESTo_reactor (Buffer_reactor):
        
        def __init__ (self, react):
                Buffer_reactor.__init__ (self)
                self.presto_react = react
        
        def __call__ (self, *args):
                apply (self.presto_react, args)
                self.presto_react = None
                self.buffer ('<presto xmlns="http://presto/" />')
                self.buffer ('') # ... buffer_react ()
                                

class PRESTo_async (Loginfo, Finalization, XML_element):

        def finalization (self, instance):
                self.log ('<finalized />')

        xml_name = u'http://presto/ presto-async'

        presto_interfaces = set ()
        
        def presto (self, reactor):
                assert None == self.log ('<presto/>', '')

        presto_methods = {}


class PRESTo_reactor_sync (Buffer_reactor):
        
        def __init__ (self, select_trigger):
                self.select_trigger = select_trigger
                Buffer_reactor.__init__ (self)
                
        def __call__ (self, data):
                assert type (data) == types.StringType
                self.select_trigger (lambda m=self, d=data: m.buffer (d))


class PRESTo_sync (PRESTo_async, Synchronized):

        def presto_synchronized (self, reactor, method):
                # instanciate a new reactor, with a copy of the PRESTo request
                # state and thunk through the synchronized thread loop queue
                # a call to the class method named.
                #
                xml_reactor = PRESTo_reactor_sync (
                        self.synchronizer.select_trigger
                        )
                xml_reactor.presto_vector = reactor.presto_vector.copy ()
                self.synchronized (
                        lambda x=self, r=xml_reactor:
                        x.__class__.__dict__[method] (x, r)
                        )
                return xml_reactor
                #
                # returns the stallable buffer reactor that can be safely
                # accessed from the synchronized (threaded) method.
                
        # Note that synchronized methods *must* be class-methods.
        #
        # TODO: add support for synchronized unbound and instance methods
        #       checking the x instance first instead, or should synchronized
        #       methods allways be class-bound?
        
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
        return lambda s, r, m=method: s.presto_synchronized (r, m)
        #
        # a lambda factory to wrap PRESTo methods with an appropriate
        # synchronizer, the PRESTo_sync.presto_synchronized method.

class PRESTo_folder (PRESTo_async):
        
        # A PRESTo_folder interface implemented with a BSDDB table
        #
        # If a matching path is not found in the table, the folder will
        # by default return an new PRESTo_async instance, in any case.
        
        xml_name = u'http://presto/ folder'
        
        presto_interfaces = set ()
        
        def presto (self, reactor):
                return presto_xml (self.__dict__)
        
        def presto_folder (self, path):
                root = PRESTo_async ()
                root.presto_interfaces = self.__class__.presto_interfaces
                root.presto_methods = self.__class__.presto_methods
                self.synchronized (
                        lambda s=self, p=path, r=root: s.bsddb_folder (p, r)
                        )
                dom = XML_dom ()
                dom.xml_root = root
                return root

        presto_methods = {}


# The PRESTo root, loading and unloading Python modules, XML namespace to
# classes mapping. To mixin with the appropriate network protocol root,
# like http_server.HTTP_root or any other implementation of this interface.
#
# What's *specially* nice with the asynchronous design is that Python
# modules reload is both efficient (reloading an identical module is
# as fast as checking source identity, apparently ;-) and safe. Indeed
# loading a new module *will* block the peer until it is compiled,
# but doing it in a thread is just planning failure. Think about why you
# would reload a module in a web application peer. Debug during development
# or maintenance of a production run. When developing performance does
# not matter. And it certainly does matter a lot less than stability when
# maintaining a runtime environnement!
#
# Asynchronous is as fast as a safe network peer can get ;-)
#
                
def _None_factory (): pass
                
class PRESTo_root (Loginfo):
        
        def __init__ (self, path):
                self.presto_path = path
                self.presto_handlers = []
                self.presto_classes = {}
                self.presto_modules = {}
                self.presto_cached = {}
                for filename in self.presto_modules_dir ():
                        self.presto_module_load (filename)
                
        def __repr__ (self):
                return '<presto-root path="%s"/>' % self.presto_path

        def presto_modules_dir (self):
                return [os.path.basename (n)
                        for n in glob.glob (self.presto_path + '/*.py')]

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
                                hasattr (presto_module, 'presto_reload')
                                ):
                                presto_module.presto_reload ()
                except:
                        self.loginfo_traceback ()
                        return
        
                # update this PRESTo root XML namespace to classes mapping
                # with any module's name that has an 'xml_name' attribute.
                #
                assert None == self.log (
                        '<load-module filename="%s" id="%x"/>' % (
                                filename, id (presto_module)
                                ), ''
                        )
                self.presto_modules[filename] = presto_module
                if not hasattr (presto_module, 'presto_components'):
                        presto_module.presto_components = ()
                self.presto_classes.update (dict ([
                        (item.xml_name, item)
                        for item in presto_module.presto_components
                        ]))

        def presto_module_unload (self, filename):
                presto_module = self.presto_modules.get (filename)
                if presto_module == None:
                        return
                        
                assert None == self.log (
                        '<unload-module filename="%s" id="%x"/>' % (
                                filename, id (presto_module)
                                ), ''
                        )
                for item in presto_module.presto_components:
                        del self.presto_classes[item.xml_name]
                del self.presto_modules[filename]
        
        def presto_dom (self, reactor, path):
                # Check for an reference for that path in the root's cache
                # and if there is one, try to dereference the DOM instance,
                # and return True if the method succeeded to attach such
                # instance to the reactor.
                #
                reactor.presto_dom = self.presto_cached.get (
                        path, _None_factory
                        ) ()
                return reactor.presto_dom != None
                
        PRESTo_FOLDER_MAX_DEPTH = 4
                
        def presto_folder (self, reactor, path, separator):
                # Implements a cache folder lookup, starting from the right
                # of the path and walking up the root's cache to find a
                # containing "folder" DOM instance. Obviously not something
                # you'd want for a public server but which is very convenient
                # for a peer.
                #
                base, path = path.rsplit (separator, 1)
                while base:
                        presto_dom = self.presto_cached.get (
                                path, _None_factory
                                ) ()
                        if (
                                presto_dom != None and
                                hasattr (presto_dom.xml_root, 'presto_folder')
                                ):
                                root = presto_dom.xml_root.presto_folder (
                                        base, path
                                        )
                                if root != None:
                                        self.presto_cache (
                                                reactor,
                                                separator.join ((
                                                        base, name
                                                        )),
                                                '/'.join ((
                                                        presto_dom.presto_path,
                                                        name
                                                        )),
                                                root
                                                )
                                if reactor.presto_dom != None:
                                        return True
                                
                        base, name = base.rsplit (separator, 1)
                        path = separator.join ((path, name))
                return False
                #
                # As its many levels of indentation show, this may be a
                # "busy-loop" that consume CPU time when confronted with
                # unmatched long path (with many separators, I mean).
                #
                # However, the worst-case scenario is one of a deliberate
                # attack or absurd use of a PRESTo server for deeply-nested
                # static web site. For the intended use case (a web peer),
                # this folder interface provides a mean for any instances
                # to "catch" requests for the URLs they "contain".

        def presto_cache (self, reactor, path, filename, root=None):
                # Load a DOM in the root's cache, either from an XML file
                # or from a string. The path and filename must be provided
                # to create the DOM instance, the XML string is optional.
                #
                assert None == self.log (
                        '<cached count="%d"'
                        '/>' % len (self.presto_cached), ''
                        )
                reactor.presto_dom = XML_dom ()
                reactor.presto_dom.xml_classes = self.presto_classes
                reactor.presto_dom.presto_path = path
                if root == None:
                        reactor.presto_dom.xml_parser_reset ()
                        root = reactor.presto_dom.xml_parse_file (
                                open (filename, 'r')
                                )
                elif type (root) == StringType:
                        reactor.presto_dom.xml_parser_reset ()
                        root = reactor.presto_dom.xml_parse_string (root)
                elif not hasattr (root, 'xml_name'):
                        reactor.presto_dom.xml_root = None
                if root == None:
                        root = PRESTo_async ()
                        root.xml_name = u'http://presto/ xml-error'
                        root.xml_first = u'XML error!' # TODO: explicit ...
                if not root.xml_attributes:
                        root.xml_attributes = {}
                reactor.presto_dom.xml_root = root
                self.presto_cached[path] = weakref.ref (reactor.presto_dom)

        def presto_commit (self, dom):
                # commit the instance's state to the file system
                open (dom.presto_path, 'w').write (
                        ''.join (xml_prefixed (dom.xml_root))
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
        #     the purpose of this implementation is filter out undefined
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
                                             

class PRESTo_benchmark:
        
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


def presto_producer (reactor, result, encoding='ASCII', benchmark=None):
        # return one single Composite_producer with a simplistic PRESTo
        # envelope made of two elements: the accessed DOM root and the 
        # byte string, unicode string, xml element or producer returned by
        # a call to presto_rest.
        #
        e = XML_element ()
        e.xml_name = u'http://presto/ PRESTo'
        e.xml_attributes = reactor.presto_vector
        e.xml_children = [result, reactor.presto_dom.xml_root]
        if benchmark != None:
                e.xml_children.append (PRESTo_benchmark (benchmark))
        head = '<?xml version="1.0" encoding="%s"?>' % encoding
        if reactor.presto_dom.xml_pi:
                head += xml_pi (reactor.presto_dom.xml_pi, encoding)
        return Composite_producer (head, xml_prefixed (
                e, reactor.presto_dom.xml_prefixes, 
                xml_ns (reactor.presto_dom.xml_prefixes), encoding
                ))


# Five Points of Articulation, Five Degrees of Freedom
#
# Allegra's PRESTo uses Python and the standard four points of articulation
# to build a development stack for application peers:
#
# 1. XML               Data Model | File System, BSDDB, ...
# 2. Python            API | Asynchronous State, Synchronized Methods, ...
# 3. XSLT              Display | Themes, Localization, ...
# 4. CSS               Look & Feel | Font, Colors, ...
# 5. JavaScript        Local User Interaction
#
# Although there is no such thing as a "common" web application, those five
# points provide enough degrees of freedom to develop the most complex
# statefull web peer applications you can dream of ... or write a quick and
# dirty CGI script (which is what you should do first, of course).
#
#
# Purpose: To Implement Asynchronous/Synchronized Instance Methods
#
# This design supposes that there will be two broad kind of interfaces
# implemented for each XML document type: long-running process, much like
# an old synchronous script associated at first with that "page", and
# then a set of asynchronous and/or properly synchronized new interfaces,
# possibly common to many different "pages", like for instance DB functions.
#
#
# Not Just HTTP
#
# PRESTo is not necessarily an HTTP protocol. Nothing prevents this module to
# be used to develop other persistent statefull network peer, for instance
# SMTP agents and other MIME protocols. PRESTo is just a Python implementation
# of a simple Persistent REST Object interface. There is nothing "HTTP"
# specific about that interface (TODO: smtp_presto.py, etc ...).
#
# You may very well implement XML/RPC or SOAP "over" PRESTo, and possibly a
# lot simpler and faster than using a general purpose serializer. But only
# when http_server and http_presto handle POST methods methods ...
#
#
# Python API
#
# PRESTo is very much a practical protocol, and a very opportunistic one.
#
# Instead of complex Interface/Component model, I just used two simple
# class properties:
#
#        presto_interfaces = set ()
#        presto_methods = {}
#
# a "default" method and a single CGI-like interface:
#
#        presto (self, reactor)
#
# mixed with Loginfo, Finalization and XML_element interfaces, "managed" by
# a multi-purpose handler and "hosted" by a generic, filesystem-like
# interface with a filesystem implementation.
#
# A vector of UNICODE strings as input:
#
#        (u'key': u'value', ...)
#
# for instance an HTTP urlencoded (in UTF-8) GET form request like:
#
#        GET /path?key=value HTTP/1.1\r\n
#        Host: 127.0.0.1
#
# is translated as a call to the 'presto' method of the instance serialized
# as the root element from the XML document named '/path' in the root
# filesystem associated with host "127.0.0.1" (by default it is found
# in "~allegra/presto/127.0.0.1/path").
#
# The method invoked may set its own . If it does not the instance returned by
# the methodResults is considered as:
#
#         XML (instance.state) + XML(instance.function (REST))
#
# What Allegra's add to that simple REST specification is a bit of
# namespace for another response enveloppe than SOAP or XML/RPC to bundle
# the bounded instance state and the result of the function called.
#
# Plus persistence for Python object instances (the P and o in PRESTo).
#
# The default implementation of persistence uses a filesystem, but such
# interface may be easely developped for a BSDDB, a la ZODB. A simple
# roadmap is to provide an interface compatible with os.stat (). Obviously
# access to a single BSDDB file may be faster than a complete filesystem.
# See the BSDDB_folder example for a modular implementation of a trivial XML
# Object Database. Instead of forcing to choose between a practical filesystem
# and a fast database file, Allegra offers both, mixing them gracefully.
#
#
# Encodings
#
# PRESTo uses the default encodings of xml_dom.py: instanciate UNICODE
# strings and serialize to any UNICODE codec provided by Python and
# supported by the accessor (or ASCII by default).
#
# Aside the fact that not all PRESTo accessors should be expected to support
# anything else than ASCII, there is a practical opportunity to make a
# distinction between input data. In a PRESTo applications, UNICODE strings
# can be identified as beeing instanciated from an XML document or a
# PRESTo request, they are "public" resources, directly accessible by the
# application user. They are "original" input and state. Other types are more
# likely to be "private" or "derived" and inaccessible state. 
#
# As implemented by presto_prompt.py's, "browsing" PRESTo instances from a
# browser makes it clear what the user inputed and what the program
# instanciated.
#
# 
# Synchronize
#
# Synchronized methods are passed a callable instance that behaves much like
# the print statement
#
# import time
#
# class Hello_world_sync (PRESTo_sync):
#
#        presto_interfaces = Set (('PRESTo', ))
#
#        def hello_world (reactor):
#                reactor ("hello ...")
#                time.sleep (3)
#                reactor (" world")
#                reactor ("")
#
#        presto_methods = {
#                'HelloWorld': presto_synchronize ('hello_world')
#                }
#
# the presto method is where to implement the synchronous
# function, that is any blocking function like access to
# synchronous API's, etc ...
#
# besides filesystem and DB access, the most common
# application of this interface is ... CGI scripting, or
# any other form of synchronous code that is not broken and
# should not be fixed. Just replace "print" with the
# "reactor ()" method, et "voila!", presto.
#
# to thunk back to the async_loop.loop, use the select_trigger
# attached to the reactor parameter:
#
#        ractor.select_trigger ()
#
#
# XML to Python serialization (xml_dom)
#
# Python to XML serialization
#
# The presto_xml function is a generic way to represent a Python instance
# *tree* as an XML string.
#
# This is a "bullet-proof" implementation that uses the Python
# serialization interfaces, that does not raise exceptions and
# allways returns a valid XML string. The purpose is not to
# provide another pickling implementation (you can't instanciate
# back the instance serialized) but to produce XML usefull for
# presentation, XSL transformation or some form of XML/RPC.
#
# See presto_prompt.py for sample applications.
#
# There is *one* right way to do it.
#
# This way produces practical "flat" XML trees for Python instance
# used to hold state, yet can also serialize collections of nested
# but simple datastructures. One thing it will not do is dump "deep"
# states and recurse dangerously. Statefull datastructures tend to
# establish circular links, and are not safe to recurse without
# checking for circular references. On the other end, function
# results may reference the same instance and yet require them to
# be serialized repeatedly.
#
# Last but not least, this way allows developpers to reflect the
# attributes assigned to instance transparently in the XML string
# produced.
#
#
# Persistence
#
# Note that this is an asynchronous (ie blocking) persistence
# implementation, as it should actually be. Instances should
# be fast to instanciate, not slow or stalling! Move the
# long-running and blocking process to synchronized method invoked
# thereafter, don't keep them in the __new__, __init__ or xml_valid
# methods.
#
# The benefit of keeping *all* instanciations asynchronous
# is a much simpler design and implementation of the application
# peer. The cost is two blocking system call to a synchronous
# file system. Yet an application peer is expected to do a lot more
# "view" of its cache than persistence "read" or "write" of the
# objects it hosts.
#
# If however you absolutely need to provide your own persistence - 
# for instance threaded synchronous access to a BSDDB - implement
# a folder interface and subclass the 'load' and 'save' interfaces
# of the XML root elements attached by their "containing" folder.
#
# Or see 
#
#        bsddb_presto.BSDDB_folder
#
# for an implementation of a persistent folder stored synchronously
# (queued in the same thread loop, that is) in a BSDDB hash table.
# 
#                
# Performances
#
# Once optimized PRESTo should be a *fast* and *scalable* solution.
#
# Cached PRESTo doclets that are handled asynchronously are as fast as pushing
# a short XML message back to the browser. An HTTP response can also stall a
# session waiting for some asynchronous continuation or a threaded response,
# but it will not block requests of other sessions or any other tasks performed
# by the peer.
#
# It is debattable wether a Python peer can outperform a J2EE, .NET or even
# a LAMP implementation, but the fact remains that an asynchronous PRESTo peer
# can manage its memory a lot more efficiently, and also provide an integraded
# development environnement with a safe runtime host, in the sense that all
# data structures are instanciated and accessed asynchronously. And fast.
#
# Real fast, when properly cached, which is quite easy when all memory
# is available to the application itself and not globbed by it host ;-)
#
#
# Finalizations
#
# XML peerlets are also asynchronous Finalizations holded by a simple session
# cache. Peerlets are finalized when not more session that accessed it is
# holding its reference. When you close your browser's session to Allegra's
# web server, all the XML objects you accessed will be finalized and released
# from memory if no other reference to it is holded (for instance by a defered
# event like a POP mailbox recurrent check).
# 
# The default finalization of XML peerlet instances is to serialize itself
# to the debug log. In effect, any XML document "published" acts as a template
# for a transient instance in memory as long as the session stays open. But
# it is a trivial task to add persistence to it (just serialize it to another
# file than STDERR, or to bsddb, or MySQL, or ... etc).
#
#
# Make No Mistake! PRESTo is not a toy.
#
# This is a simple, robust, productive, proven, cross-plateform development
# platform and runtime host for distributed applications. Allegra's PRESTo
# has all it takes to be an "industrial strength" infrastructure for the
# development and deployement of entreprise internet applications.
#
# No kinding?
#
# Well, check it out by yourself. It has:

# 0. High Performances - High Availability
#
#    Distributed Web Application Peers scale better than Web Application
#    Servers like IIS or the many J2EE implementations. And they perform
#    better if properly cached. A lot better.
#
#    Instead of one thread/process per request/session, and all the memory
#    and CPU cycle that consume *synchronously*, there is one process with
#    a large pool of memory available to cache asynchronous states.
#
#    You may mix-in synchronized methods, easely audit their thread-safety
#    and restrict their CPU resources to an array of threads.
#
#    The result is an application peer that his more resilient in the face
#    of flooding and breaks only when it runs out of memory. Distributed on
#    a network, such application is practically resilient, or Highly
#    Available.
#
#
# 1. The best programming language implementation available today.
#
#    As an application host and network peer, the CPython VM as a proven track
#    record of reliability, performance and portability. Unlike Java, and
#    much like C#, Python is an C implementation, not a formal specification
#    (there is a "standard programming language", it's called LISP, and there
#    is a "standard operating system language implementation" and it's that
#    good old "C" ;-). Beeing also free software, Python has the advantage of
#    both Java and C#: it is not suprising that - unlike Perl - Python has
#    been reimplemented in Java and C#.
#
#    Perl has no equivalent, yet its Regular Expression (RE) language has
#    been ported to most development platforms, including Python. 
#
#    Python combines the power of RE, comes with first-class UNICODE support
#    (Adobe Acrobat 7.? appear to includes some 1999 Python codecs ;-) and
#    integrates the BSDDB and expat libraries, the de-facto public standards
#    implementation of relational databases and XML applications.
#
#
# 2. Simplicity.
#
#    Allegra PRESTo's sources are several orders of magnitude shorter
#    than a functionnaly equivalent J2EE implementation. Similarly the
#    applications written with it may be proportionnally shorter and
#    simpler. Which means that both Allegra and its applications are
#    less expensive to develop, audit and maintain; and that development
#    of both yields lower safety risks and better quality. Eventually,
#    that is what "entreprise software" is all about: a higher ROI and
#    lower capital risks. 
#
#
# 3. Productivity.
#
#    The well-articulated development process of a PRESTo application serves
#    a very important purpose for "entreprise software development":
#    developpers accountability. Deliverables for every "points of
#    articulation" in the application development can be associated with a
#    practically usefull specification: XML DTD and sample documents, demo
#    functional interfaces, possibly made of components, and presented
#    with style.
#
#
# 4. IDE. Allegra's PRESTo development stack is fully supported by Eclipse
#    and its Python, XML, CSS and JavaScript pluggins. 

# Note about this implementation
#
# The purpose of xml_producer.py is to allow REST/AJAX developper (like me ;-)
# to "bundle" a persistent state, a set of functions and their results as one
# XML document pushed asynchronously on a stallable channel. It's an effective
# way to allow trivial implementations of asynchronous data flow aggregation
# and serialization.
#
# But it might also be applied to other XML network protocols, like SOAP,
# XMLRPC, etc ...
#
#
# True Concurrent State, Asynchronously
#
# One very unorthodox feature is the implied late-state serialization to the
# client. Suppose that several client access a method of the same XML element 
# instance and receive as response the XML string of the state of the tree
# below that element plus an XML string providing the function result. Like
# this:
#
#        <PRESTo!>
#                <my-result>
#                My function's result
#                </my-result>
#                <our-element>
#                Our XML State of this Instance and <its-child/> ...
#                </our-element>
#        </PRESTo>
#
# Using an XML_producer for both result and element will yield a interesting
# and quite practical feature for an Internet application server. Concurrent
# access to the same instance will produce the expected behaviour and return
# to the different clients a "true state" over a slow and unpredictable
# network. If client A update the state of "our-element" and that it cannot
# retrieve its response before B also modify that state, then its response
# will include both updates. Ditto for B. If A and B concurrently update the
# same state they will "view" both updates. Asynchronously :-)
#
# Since concurrent access to the same state yields a "correct" state to the
# client, transaction logic is a lot simpler to implement and does not require
# a centralized "transactional" SQL database. For instance, a stock
# represented as the XML document and bound to a Python instance can be
# accessed by two different agents concurrently and yet display the "real"
# level of the stock.
#
# Remember that PRESTo is not confined to Web User Interfaces. An transaction
# for a purchase order may include stock level check using the same interface
# but dropping all XSLT/CSS/JavaScript part of the stack. Ditto for AJAX
# (or is it good old Client/Server?). PRESTo can be used to develop complex
# transactional applications without relying on a transactional SQL database.
# 
# Relational Databases are usefull to process large volumes of data, they are
# not *that* good at holding state and managing transactions. If most RDBMS
# implementations provide all those transactional features, the concept of a
# centralized synchronous state holded by a single server and data model
# has some terrible consequences on both the computer application development,
# and the computer system it runs on.
#
# The popular "object database" design is a lot more effective in providing
# a degree of freedom to a relational data model and allowing an easier
# distribute off the application on a computer network.
# 
# The PRESTo host is another such object request broker, but asynchronous
# and a lot simpler.
#
#
# Fast.
#
# Now you can use all that memory not to host Apache but a cache of a web
# message board. One that can handle the load of massive concurrent access
# and still blast the true state of its cache to all clients.
#
#
# Practical
#
# This design allows a faster and simpler generation of XML than 
# serialization of data structure. By letting the XML dom accessor attach
# simple XML producers or XML strings *allready* serialized and bypass the
# process of instanciation/serialization ... in any language ;-)
#
# Think about asynchronous workflow with persistent web interfaces!
#
# You can attach to an XML element tree  a few set of Buffer_reactor wrapping
# asynchat collectors and let the REST handler take care of aggregating a
# REST response. It is simple, practical and ... very efficient.
#
# Wether is takes less than a millisecond or more ten seconds to aggregate all
# data, the HTTP response head and the first part of the XML response will
# be sent asap to the browser. The perceived speed of the response is fast
# because the server articulates its responses and let the client process
# aggregated serialized data in two chunks: state first, results second.
#
# Another application of XML producers is synchronized persistent REST
# object interfaces (or PRESTo). REST method pushed to a thread loop queue
# can stall and refill a Buffer_producer attached to the XML instance bounded.
#
# As the threaded REST method thunks appends strings to the Buffer_reactor
# (via the select_trigger), the XML producer sends those strings to the
# client browser as they are produced or stall the HTTP server channel, until
# the threaded REST method exits, then finally completes the XML response.
#
