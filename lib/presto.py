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

import types, glob, os, stat, imp, weakref, time

from xml.parsers import expat

if os.name == 'nt':
        allegra_time = time.clock
else:
        allegra_time = time.time

from allegra import (
        loginfo, finalization, thread_loop, 
        producer, reactor, xml_dom, xml_unicode
        )


# TODO: move away ...

class PRESTo_reactor (producer.Stalled_generator):
        
        def __init__ (
                self, react, response='<presto xmlns="http://presto/" />'
                ):
                self.presto_react = react
                self.presto_response = response

        def __call__ (self, *args):
                self.presto_react (*args)
                self.generator = iter ((self.presto_response,))
                self.presto_react = None


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

class PRESTo_reactor_sync (reactor.Buffer_reactor):
        
        def __init__ (self, select_trigger):
                self.select_trigger = select_trigger
                reactor.Buffer_reactor.__init__ (self)
                
        def __call__ (self, data):
                assert type (data) == types.StringType
                self.select_trigger ((self.buffer, (data,)))

class PRESTo_sync (PRESTo_async):

        "A component to synchronize threaded methods."

        xml_name = u'http://presto/ sync'
        
        synchronizer = None
        synchronizer_size = 16
        
        def __init__ (self, name, attributes):
                xml_dom.XML_element.__init__ (self, name, attributes)
                thread_loop.synchronized (self)
                
        def xml_valid (self, dom):
                self.xml_dom = dom 
                #
                # a synchronized element *must* provide a circular reference
                # through the cache. this prevents a big: 
                #
                # thread trashing
                #
                # too early death of the weakref in the cache and a horde 
                # of thread-queues and select_triggers to be instanciated, 
                # opened and closed, with all the problems associated.
                #
                # and a "busy-body" cache behaviour is not usefull for
                # something long-lived like a database connection, a CPU
                # intensive process, etc ... things that are meant to be
                # cached as long as possible.
        
        # Note also that there are two logging interfaces for a synchronized
        # PRESTo instance, asynchronous and synchronous:
        #
        #       self.log ('async')
        #
        # and
        #
        #       self.synchronizer.log ('sync')
        #
        
def presto_synchronize (method):
        def sync (element, reactor):
                xml_reactor = PRESTo_reactor_sync (element.select_trigger)
                xml_reactor.presto_vector = reactor.presto_vector.copy ()
                element.synchronized ((method, (element, xml_reactor)))
                return xml_reactor
                
        return sync
        #
        # a method factory that "wraps" the asynchronous PRESTo reactor 
        # handled with a synchronized buffer reactor before passing it
        # to the "decorated" method.


# An Asynchronous Component Object Model

class PRESTo_dom (
        xml_dom.XML_dom, loginfo.Loginfo, finalization.Finalization
        ):
        
        presto_defered = None
        
        def __init__ (self, name, types={}, type=PRESTo_async):
                self.xml_prefixes = {u'http://presto/': u'presto'}
                self.xml_pi = {}
                self.xml_type = type
                self.xml_types = types
                self.presto_name = name
                        
        def __repr__ (self):
                return 'presto-dom name="%s"' % self.presto_name
                        
        # The PRESTo commit and rollback interfaces
        
        def presto_rollback (self, defered):
                self.xml_parser_reset ()
                try:
                        self.xml_expat.Parse (
                                open (self.presto_name, 'r').read (), 0
                                )
                except expat.ExpatError, error:
                        self.xml_expat_ERROR (error)
                self.xml_expat = xml_parsed = None
                if self.xml_root == None:
                        self.xml_root = PRESTo_async (
                                u'http://presto/ async', None
                                )
                if self.xml_root.xml_attributes == None:
                        self.xml_root.xml_attributes = {}
                defered[0] (*defered[1])
                return True
        
        def presto_commit (self, defered):
                open (self.presto_name, 'w').write (
                        xml_unicode.xml_document (self)
                        )
                return True


# Loading and unloading Python modules, XML namespace to types mapping.
                
def none (): pass
                
PASS = (none, ())
                
class PRESTo_root (loginfo.Loginfo):
        
        presto_type = PRESTo_async
        
        def __init__ (self, path):
                "load all Python in modules/ and all components in root/"
                self.presto_path = path + '/root'
                self.presto_path_python = path + '/modules'
                self.presto_types = {}
                self.presto_cached = {}
                self.presto_modules = {}
                for filename in self.presto_modules_dir ():
                        self.presto_module_load (filename)
                for filename in glob.glob (self.presto_path + '/*'):
                        if stat.S_ISREG (os.stat (filename)[0]):
                                self.presto_cache (
                                        '/' + os.path.basename (filename), 
                                        PASS
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
                "list all modules's name found in modules/"
                return [os.path.basename (n) for n in glob.glob (
                        self.presto_path_python + '/*.py'
                        )]

        def presto_module_load (self, filename):
                "load a named Python module"
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
                        return self.loginfo_traceback ()
        
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
                "unload a named Python module"
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
                "route a request to its reactor.presto_dom component"
                #
                # Check for a reference in the root's cache for that path or 
                # for a folder that contains it and if there is one, try to 
                # dereference the DOM instance.
                #
                # return True if the method succeeded to attribute such 
                # instance to the reactor.
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
        
        def presto_cache (self, path, rolledback=PASS, reactor=None):
                # instanciate a DOM, cache its weak reference, roll it back
                # and defer the PRESTo continuation ...
                #
                dom = PRESTo_dom (
                        self.presto_path + path, 
                        self.presto_types, 
                        self.presto_type
                        )
                self.presto_cached[path] = weakref.ref (dom)
                if reactor != None:
                        reactor.presto_dom = dom
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
        dom, attributes, result, encoding, globbing=1<<14 # 16KB glob
        ):
        # return one single Composite with a simplistic PRESTo
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
        return producer.Composite (
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
        # return one single Composite with a simplistic PRESTo
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
        return producer.Composite (
                head, xml_unicode.xml_prefixed (
                        e, prefixes, xml_unicode.xml_ns (prefixes), encoding
                        ), globbing
                )


# the core PRESTo interfaces/implementation itself, just REST

# Types with safe __str__ 

PRESTo_Unicode = types.UnicodeType

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
        attributes=' xmlns="http://presto/"', encoding='ASCII',
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
                return '<iter%s>%s</iter>' % (
                        attributes, 
                        ''.join ((
                                presto_xml (i, walked, '', encoding)
                                for i in instance
                                if not id (i) in walked
                                ))
                        )
        
        elif isinstance (instance, dict) and not instance_id in walked:
                # 4. dictionnary
                walked.add (instance_id)
                items = ((
                        presto_xml (k, walked, '', encoding),
                        presto_xml (v, walked, '', encoding)
                        ) for k, v in instance.items ())
                return '<map%s>%s</map>' % (
                        attributes,
                        ''.join ((
                                '<item>%s%s</item>' % i
                                for i in items if i[0] or i[1]
                                ))
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

        # Note
        #
        # This function is slightly faster than a simple generator derived
        # from it. Optmization in Python then in C may yield significant
        # improvement ...


def presto_ctb (ctb):
        return '<excp xmlns="http://presto/">%s</excp>' % presto_xml (
                ctb, set (), ''
                )

def presto_rest (method, component, reactor):
        try:
                result = method (component, reactor)
        except:
                return presto_ctb (loginfo.loginfo_traceback ())
                                
        if result == None:
                # None return <presto/>
                return '<presto xmlns="http://presto/" />'
                
        if (
                type (result) in (str, unicode) or 
                hasattr (result, 'xml_name') or
                hasattr (result, 'more')
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

# TODO: get the XML namespaces prefixes issue right (optimize for 8-bit
#       byte string dump and an unprefixed PRESTo namespace, this *is*
#       the framework context ...).