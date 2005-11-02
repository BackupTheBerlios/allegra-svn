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

import re, types

from allegra.prompt import compact_traceback, python_prompt
from allegra.producer import Simple_producer
from allegra.xml_unicode import xml_attr
from allegra.xml_dom import XML_element
from allegra.presto import presto_xml, presto_synchronize


# The PRESTo XML flavour of Python's builtin dir()
#
# Instead of a simple list of names, this one returns the tuple:
#
#        (base, dir (instance), instance.__dict__)
#
# allowing the browser to display at once the instance attributes as well
# as its full state. it may be slow on roots of large instance trees (like
# the PRESTo_root of a busy peer) but for browsing the peer states, it
# really shines.

_RE_dir_of = re.compile ('^.*?[(](.*?)[)]$')

PRESTo_types = (types.InstanceType, types.ObjectType,)

class _NO_INSTANCE: pass

def presto_xdir (self, instance):
        walked = (
                id (self.presto_prompt_env['__builtins__']),
                id (self.presto_prompt_env)
                )
        e = XML_element ()
        e.xml_name = u'http://presto/ dir'
        if instance != _NO_INSTANCE:
                names = dir (instance)
                if type (instance) in PRESTo_types:
                        names = set (names).difference (
                                set (instance.__dict__.keys ())
                                )
                e.xml_attributes = {u'base': _RE_dir_of.match (
                        self.presto_prompt_line
                        ).groups ()[0]}
        else:
                names = self.presto_prompt_env.keys ()
        e.xml_children = [
                presto_xml (instance, set (walked)),
                presto_xml (names, set ())
                ]
        if type (instance) in PRESTo_types:
                e.xml_children.append (presto_xml (
                        instance.__dict__, set (walked)
                        ))
        # self.presto_prompt_env['__builtins__'] = None
        return e
        
        
def presto_prompt_async (self, reactor):
        # 0. if no prompt line, return None
        #
        self.presto_prompt_line = reactor.presto_vector.get (u'prompt')
        if not self.presto_prompt_line:
                return
                
        # 1. setup the interpreter environement and decode the
        # prompt line submitted,
        #
        if self.presto_prompt_env == None:
                self.presto_prompt_env = {}
        self.presto_prompt_env['xdir'] = (
                lambda x=_NO_INSTANCE, s=self:presto_xdir (s, x)
                )
        self.presto_prompt_env['self'] = self
        self.presto_prompt_env['reactor'] = reactor
        #
        # 2. eval or execute, report the method as either 'eval',
        # 'exec' or 'excp' and the result (or the exception) and
        # delete the reference set to the handler and the reactor
        # (to prevent circular reference and ensuing memory
        # leak) then return the XML producer.
        #
        method, result = python_prompt (
                self.presto_prompt_line, self.presto_prompt_env
                )
        # do not walk the __builtins__ or the prompt environnement
        # dictionnary when serializing Python instance trees in
        # presto_xml ...
        #
        walked = (
                id (self.presto_prompt_env['__builtins__']), 
                id (self.presto_prompt_env)
                )
        # remove any references to the instance and the reactor from
        # the prompt environnement (and xdir is one!)
        #
        del self.presto_prompt_env['xdir']
        del self.presto_prompt_env['self']
        del self.presto_prompt_env['reactor']
        try:
                # make sure the _ reference is deleted from the
                # eval/exec __builtins__ dictionnary, and avoid
                # nasty infinite loop in presto_xml ...
                #
                del self.presto_prompt_env['__builtins__']['_']
        except:
                pass
        #
        # 3. either pass a XML element, a producer, or the Python
        # instance presto_xml string as a result. Note that None
        # simply result in an empty element.
        #
        if method == 'excp':
                result = presto_xml (result, set (walked))
        elif hasattr (result, 'xml_name') or (
                result != reactor and hasattr (result, 'more')
                ):
                e = XML_element ()
                e.xml_name = u'http://presto/ %s' % method
                e.xml_children = [result]
                return e
                
        elif self.presto_prompt_env.has_key ('__builtins__'):
                result = presto_xml (result, set (walked))
                del self.presto_prompt_env['__builtins__']
        return (
                '<presto:%s'
                ' xmlns:presto="http://presto/"'
                ' >%s</presto:%s>' % (method, result, method)
                )
        # 4. continue ...
        #
        # return a string or an element, let the Composite_producer
        # do the right thing and glob all strings if possible to refill
        # the a 16KB buffer for instance.
        #
        # Using an XML tree *is* slower than generating the ad-hoc
        # XML string for a simple case, but the possibility to
        # return an XML tree yields a lot more applications. And
        # optimization can be done once, in an xml_string.c module.
        #
        #        "measure twice, cut once"
        #
        # Then optimize.
        #
        # In this case, at the *developper* prompt, the full power
        # of PRESTo is still available: you can evaluate a producer
        # or an XML element for what they are in the context of
        # PRESTo, not just as Python instances.


def presto_prompt_sync (self, reactor):
        line = reactor.presto_vector.get (u'prompt')
        if not line:
                reactor ('<presto:presto xmlns:presto="http://presto/" />')
                reactor ('')
                return
        
        try:        
                env = self.presto_prompt_env.copy () # not thread-safe!
        except:
                env = {} 
        env['reactor']= reactor
        env['self'] = self
        method, result = python_prompt (line, env)
        reactor ('<presto:%s xmlns:presto="http://presto/">' % method)
        reactor (presto_xml (result, set ()))
        reactor ('</presto:%s>' % method)
        reactor ('')


def presto_debug_async (Debug):
        Debug.presto_prompt_env = None
        Debug.presto_prompt_async = presto_prompt_async
        Debug.presto_interfaces = (
                Debug.presto_interfaces | set ((u'PRESTo', u'prompt', ))
                )
        Debug.presto_methods = Debug.presto_methods.copy ()
        Debug.presto_methods[u'async'] = presto_prompt_async
        #
        # This is a nice example of PRESTo attribution


def presto_debug_sync (Debug):
        # wrap a Debug class with the PRESTo_prompt_sync interfaces and 
        # methods (both public and privates).
        #
        presto_debug_async (Debug)
        Debug.presto_prompt_sync = presto_prompt_sync
        Debug.presto_methods[u'sync'] = presto_synchronize (
                'presto_prompt_sync'
                )


# Note about this implementation
#
# The implementation of the PRESTo prompt is its first measure. Anyone
# interested in writing its own application to host by Allegra's PRESTo peer
# should read it carefully. It covers all important aspects of the interfaces,
# including how to access synchronized threads from asynchronous methods.
#
# You will find another measure of the Allegra XML/HTTP "meme" in the
# module bsddb_presto, which provides non-blocking synchronized interfaces to
# BSDDB databases.
#
#
# A Better Prompt
#
# The PRESTo prompt is has two big advantages over the original Medusa
# network prompt. First there may be more thant one environnement active at
# the same time, each with its own history in the browser. As many as one
# per "debugged" instance. Second, the PRESTo prompt is simpler (no multi
# line, this is the web ;-) in its core implementation and yet it is 
# browseable and extensible with static XSLT stylesheets or dynamic AJAX
# JavaScript programs.
# 
# The last difference is rather a design constraint: by default all prompt
# environnements are as transient as the debugged instance itself. Yet this
# does not prevent a prompt user to deliberately cache the environnement
# with the instance debugged, simply by entering:
#       
#        dom = reactor.presto_dom
#
# and create a circular link between the DOM instance and its root element.
#
#
# No Access Control? Use secret URI!
#
# PRESTo allows the simplest implementation of access control. It is trivial
# and safe for instance to disable this module alltogether, or restrict its
# access to authorized personnel only. Without unloading the module itself.
# Just by deleting the root.xml document from the filesystem or renaming it
# to a secret - one-time and/or cryptic - URI.
#
# With PRESTo there is only one resource to control, the filesystem. Security
# is provided to the application by enforcing a safe process of application
# resource description. Compartimenting resources into distinct "webs" of
# URI and rooting each of them with a possibly secret name (for instance
# the result of a login hash, the content of a cookie, etc ...).
#
# Application Resource Access Control (ARAC, what an ugly acronym!) is a
# matter better handled by the application. The trouble with transport
# layer authentication is that they yield only transient identification
# and that their functions are difficult to proxy.
#
# ARAC is allways implemented more-or-less independantly from HTTP or HTTPS
# authentification protocols, using a mix of cookies, names and passwords
# to do the job. Therefore there are absolutely no reasons to provide a
# PRESTo interface for HTTP basic authentication.
#
#
# Simple Component Interfaces
#
# This implementation is a test of the PRESTo interfaces as a simple "right"
# Pythonic way to declare and mixin component interfaces for synchronous
# and asynchronous implementations. It works just fine ;-)
#
# Every methods is a function like:
#
#        presto (self, reactor)
#
# which may or not be bounded.
#
# This makes it simple to "synchronize" method, dynamically update a class
# or instance interfaces, and bind a set of common functions to an instance
# or class, providing some metaphore for aspect programming (to set
# dynamically the persistence functions, like in bsddb_presto.BSDDB_folder).
#
# Here is a sample module for <my-presto/> class in the XML name space
# "http://namespace/", with a debug prompt available in a debug runtime
# environnement (an non-OOptimized CPython VM):
#
#        from allegra import presto 
#        class MyPRESTo (presto.PRESTo_async):
#                xml_name = 'http://namespace/ my-presto'
#        if __debug__:
#                from allegra import presto_prompt
#                presto_prompt.presto_debug_async (MyPRESTo)
#
#