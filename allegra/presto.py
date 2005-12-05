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

from allegra import \
        loginfo, finalization, synchronizer, \
        producer, reactor, xml_dom, xml_unicode


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
                
        # 4. try to serialize as an 8bit "representation"
        try:
                attributes += ' repr="%s"' % xml_unicode.xml_attr (
                        u'%r' % instance, encoding
                        )
        except:
                pass
        # 5. try to serialize as an 8bit string, using the default encoding
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


# Asynchronous

class PRESTo_reactor (reactor.Buffer_reactor):
        
        def __init__ (
                self, react, response='<presto xmlns="http://presto/" />'
                ):
                reactor.Buffer_reactor.__init__ (self)
                self.presto_react = react
                self.presto_response = response
        
        def __call__ (self, *args):
                apply (self.presto_react, args)
                self.presto_react = None
                self.buffer (self.presto_response)
                self.buffer ('') # ... buffer_react ()


def presto_async_commit (self, reactor):
        # commit the instance's document to the file system, blocking.
        open (
                reactor.presto_dom.presto_path, 'w'
                ).write (xml_unicode.xml_document (
                        reactor.presto_dom.xml_root, reactor.presto_dom
                        ))

# There is no need for a "rollback" method, instead dereference the
# DOM and have it be rolledback for the next call. It is a safer way
# to revert to a previous persistent state of a component instance ;-)

class PRESTo_async (
        loginfo.Loginfo, finalization.Finalization, xml_dom.XML_element
        ):
                
        def __repr__ (self):
                return '%s id="%x"' % (
                        self.xml_name.encode ('UTF-8', 'ignore'), id (self)
                        )

        def finalization (self, instance):
                self.log ('finalized')

        xml_name = u'http://presto/ async'

        presto_interfaces = set ((u'presto-host', u'presto-path'))
        
        def presto (self, reactor):
                assert None == self.log (
                        '%r' % reactor.presto_vector, 'presto'
                        )

        presto_methods = {u'commit': presto_async_commit}
        

# Synchronized

class PRESTo_reactor_sync (reactor.Buffer_reactor):
        
        def __init__ (self, select_trigger):
                self.select_trigger = select_trigger
                reactor.Buffer_reactor.__init__ (self)
                
        def __call__ (self, data):
                assert type (data) == types.StringType
                self.select_trigger ((self.buffer, (data,)))


class PRESTo_sync (PRESTo_async, synchronizer.Synchronized):

        xml_name = u'http://presto/ sync'

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
        #def presto_synchronized (self, reactor, m=method):
        #        self.presto_synchronized (reactor, m)
        #return presto_synchronized
        def synchronized (self, reactor):
                xml_reactor = PRESTo_reactor_sync (self.select_trigger)
                xml_reactor.presto_vector = reactor.presto_vector.copy ()
                self.synchronized ((method, (self, xml_reactor)))
                return xml_reactor
                
        return synchronized
        #
        # a lambda factory to wrap PRESTo methods with an appropriate
        # synchronizer, the PRESTo_sync.presto_synchronized method.


# The PRESTo root, loading and unloading Python modules, XML namespace to
# classes mapping. To mixin with the appropriate network protocol root,
# like http_server.HTTP_root or any other implementation of this interface.
                
def _None_factory (): pass
                
class PRESTo_root (loginfo.Loginfo):
        
        def __init__ (self, path):
                self.presto_path = path
                self.presto_handlers = []
                self.presto_classes = {}
                self.presto_modules = {}
                self.presto_cached = {}
                for filename in self.presto_modules_dir ():
                        self.presto_module_load (filename)
                
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
                        'load-module filename="%s" id="%x"' % (
                                filename, id (presto_module)
                                ), 'debug'
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
                        'unload-module filename="%s" id="%x"' % (
                                filename, id (presto_module)
                                ), 'debug'
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
                
        # In order to limit the possible damage of broken/malicious
        # URLs, a strict depth limit of 2 is set by default. Raise
        # to a 4 for support of a "/model/controller/view" syntax.
        #
        PRESTo_FOLDER_DEPTH = 2
                
        def presto_folder (self, reactor, path, separator):
                # Implements a cache folder lookup, starting from the right
                # of the path and walking up the root's cache to find a
                # containing "folder" DOM instance.
                #
                depth = 0
                base, name = path.rsplit (separator, 1)
                while base and depth < self.PRESTo_FOLDER_DEPTH:
                        depth += 1
                        presto_dom = self.presto_cached.get (
                                base + separator, _None_factory
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
                        # path = separator.join ((path, name))
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
                        'cached count="%d"' % len (self.presto_cached), 
                        'debug'
                        )
                reactor.presto_dom = xml_dom.XML_dom ()
                reactor.presto_dom.xml_types = self.presto_classes
                reactor.presto_dom.presto_path = path
                if root == None:
                        reactor.presto_dom.xml_parser_reset ()
                        root = reactor.presto_dom.xml_parse_file (
                                open (filename, 'r')
                                )
                elif type (root) == StringType:
                        reactor.presto_dom.xml_parser_reset ()
                        root = reactor.presto_dom.xml_parse_string (root)
                else:
                        root.xml_valid (reactor.presto_dom)
                if root == None:
                        root = PRESTo_async ()
                        root.xml_name = u'http://presto/ xml-error'
                        root.xml_attributes = {}
                elif not root.xml_attributes:
                        root.xml_attributes = {}
                reactor.presto_dom.xml_root = root
                self.presto_cached[path] = weakref.ref (reactor.presto_dom)

        def presto_commit (self, dom):
                # commit the instance's state to the file system
                open (dom.presto_path, 'w').write (
                        ''.join (xml_prefixed (dom.xml_root))
                        )


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
        e = xml_dom.XML_element ()
        e.xml_name = u'http://presto/ PRESTo'
        e.xml_attributes = reactor.presto_vector
        e.xml_children = [result, reactor.presto_dom.xml_root]
        if benchmark != None:
                e.xml_children.append (PRESTo_benchmark (benchmark))
        head = '<?xml version="1.0" encoding="%s"?>' % encoding
        if reactor.presto_dom.xml_pi:
                head += xml_unicode.xml_pi (
                        reactor.presto_dom.xml_pi, encoding
                        )
        return producer.Composite_producer (
                head, xml_unicode.xml_prefixed (
                        e, 
                        reactor.presto_dom.xml_prefixes, 
                        xml_unicode.xml_ns (reactor.presto_dom.xml_prefixes), 
                        encoding
                        ), 512 # glob 64KB
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
                                             

# Seven Points of Articulations, Eight Degrees of Freedom
#
# Allegra's PRESTo adds PNS to the standard six points of articulation in
# web development,integrates that stack for application peers:
#
# 1. PNS               Metabase | Distribution, Inference, ...
# 2. XML               Data | Aggregation, Persistence, ...
# 3. HTTP              The Network API for all services
# 4. XSLT              Display | Localisation, Transformation, ...
# 5. CSS               Look & Feel | Themes, Animation, ...
# 6. HTML              Web | User Interface, Integration, ...
# 7. JavaScript        Scripting | Interaction, AJAX, Greasemonkey, ...
#
# and provide a host for the first three. You can use Eclipse to integrate 
# development with the last four.
#
# Although there is no such thing as a "common" web application, those seven
# points provide enough degrees of freedom to develop the most complex
# statefull web peer applications you can dream of ... or write a quick and
# dirty CGI-like script (which is what you should do first, of course).
#
#
# Make No Mistake ...
#
# This is a simple, robust, productive, proven, cross-plateform development
# platform and runtime host for distributed applications. Allegra's PRESTo
# has all it takes to be an "industrial strength" infrastructure for the
# development and deployement of entreprise internet applications.
#
# And more ...
#
#
# Check It Out!
#
# Allegra PRESTo delivers:
#
# 1. High Performances and High Availability
#
#    Distributed Web Application Peers scale better than Web Application
#    Servers like IIS or the many J2EE implementations. And they perform
#    better if properly cached.
#
#    A lot better.
#
#    Instead of one thread/process per request/session, and all the memory
#    and CPU cycle this consumes *concurrently*, there is one process with
#    a large pool of memory available to cache *asynchronous* states. 
#
#    A lot of them.
#
#    An asynchronous application peer is more resilient in the face of 
#    flooding and breaks only when it runs out of memory. Distributed on
#    a network, such application is practically resilient, or Highly
#    Available.
#
#    And damn fast.
#
#    On a modest modern PC (1.5Ghz), a PRESTo request submitted by HTTP for
#    a cached instance is dispatched in much less than a millisecond when
#    handling the REST of the request is defered. 
#
#    So, practically, a modest PRESTo peer can handle more than one thousand
#    requests per seconds as long as there is enough memory available to
#    cache every instance, and that each method accessed consist in a few
#    simple lines of Python or synchronized interfaces to a fast C module
#    that is thread-safe and GIL-releasing.
#
#    Safely.
#
#    Finally, to access blocking API you can easely mix-in synchronized
#    methods, audit their thread-safety and restrict their CPU resources 
#    to a managed array of threads.
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
#    From top to toe, the library is as simple as practically possible. 
#
#    Starting from simple 8-bit Byte encoding up to complete network peer 
#    application, I tried to do remove as much as possible from the usual
#    set of features provided by industry solutions. And implement only the
#    one strictly required in the simplest possible way.
#
#    A remarkable feature of Allegra's simplicity is its logging facility,
#    which has a very practical API but also produces a simpler and better
#    encoding for Standard I/O than lines.
#
#
# 3. Productivity.
#
#    A PRESTo application can be consistently specified in XML first, then 
#    distributed to its system administrator, architect, analyst-programmers
#    and UI designers. Each one will use the same XML representation of a
#    component instance to design style sheets, program functions and test
#    the integration of a new component type of instance in a distributed 
#    metabase application.
#
#    The well-articulated development process of a PRESTo application serves
#    a very important purpose for "entreprise software development":
#    developpers accountability. Deliverables for every "points of
#    articulation" in the application development can be associated with a
#    practically usefull specification: XML DTD and sample documents, demo
#    functional interfaces, possibly made of components, and presented
#    with style.
#
#    Allegra's PRESTo development stack is fully supported by Eclipse
#    and its Python, XML, CSS and JavaScript pluggins. It blends beautifully
#    in the stack of defacto open source standards for web development.
#
#    Finally, PRESTo is a productive investment because it scales simply.
#
#    If one peer can handle one thousand request per seconds, ten PRESTo
#    peers will together handle 10 times more. And nothing in the application
#    design, architecture or infrastructure will prevent it to scale because
#    it is distributed between peer from the ground up.
#
#
# 4. For the best programming language implementation available today.
#
#    As an application host and network peer, the CPython VM as a proven track
#    record of reliability, performance and portability. Unlike Java, and
#    much like C#, Python is a C implementation, not a formal specification
#    (there is a "standard programming language", it's called LISP, and there
#    is a "standard operating system language implementation" and it's that
#    good old "C/C++" ;-). Beeing also free software, Python has the advantage
#    of both Java and C#: it is not suprising that - unlike Perl - Python has
#    been reimplemented in Java and C#.
#
#    Python combines the power of RE, comes with first-class UNICODE support
#    (Adobe Acrobat 7.? appear to includes some 1999 Python codecs ;-) and
#    integrates the BSDDB and expat libraries, the de-facto public standards
#    implementation of relational databases and XML applications.
#
#    Remarkably, the CPython has been ported from Cell phones to AS/400
#    and has integrated most desktop and server OS, including Windows, MacOSX
#    and Linux and provides excellent support for each plateform specific
#    features, including native non-blocking I/O interfaces.
#
#
# 5. Various Objections
#
#    "Python is an scripting language, you can't possibly run an
#     application server like that!"
#
#    In this asynchronous architecture, the main two bottleneck of CPython
#    for network application servers all of a sudden become features. The
#    CPython VM is known to be slow to instanciate objects and its Global 
#    Interpreter Lock (GIL)impair concurrencies of threads in order to
#    ensures reliable memory access and allocation.
#
#    From the perspective of an asynchronous loop, there are no concurrent 
#    threads and therefore, the GIL is not a problem it turns out to provide
#    a solution. The CPython VM has matured a good memory garbage collector
#    on top of this strict and lengthy allocation scheme that requires a GIL.
#    This garbage collector is used by Allegra's finalization as another
#    asynchronous event loop to implement a "cheap" but very practical 
#    programmatic effect of continuation. 
#
#    Finally, slow instanciation does matters a lot less for a statefull
#    server that can easely hold the state of thousands of users concurrently
#    without actually spending a single CPU cycle of its own.
#
#    "But Python is 100 times slower than C!"
#
#    Yes. That's why good Python applications spend most of their time 
#    executing thread-safe, GIL-releasing, compiled code from C libraries
#    like the BSDDB database module. Python applications that "glue" C
#    libraries safely together are marginaly slower than a functionnaly
#    equivalent C implementation.
#
#    Of course the "pure" Python of Allegra is slow at things like XML
#    serialization or Public Names validation, but it has allready a clear
#    C optimization strategy (Rome was not built in one day ;-)
#
#    "An asynchronous component could bring the whole server down, or do
#    many other malicious things!"
#
#    So what? Do you integrate a new component in your production run without
#    testing it first somewhere else? Do you allow to run code that has not
#    been audited as safe in your mission critical system? No, you don't.
#
#    PRESTo is as safe as you develop and implement, no more and no less. 
#
