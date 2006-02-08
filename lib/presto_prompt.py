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

from allegra import prompt, producer, xml_unicode, xml_dom, presto


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

PRESTo_types = (types.InstanceType, object)

class NONE: pass

def presto_xdir (self, instance):
        e = xml_dom.XML_element (u'http://presto/ dir', None)
        if instance == NONE:
                e.xml_children = [
                        presto.presto_xml (None, set ()),
                        presto.presto_xml (
                                self.presto_prompt_env.keys (), set ()
                                )
                        ]
                return e

        e.xml_attributes = {u'base': _RE_dir_of.match (
                self.presto_prompt_line
                ).groups ()[0]}
        walked = set ((id (self.presto_prompt_env), ))
        names = dir (instance)
        try:
                properties = set (instance.__dict__.keys ())
        except:
                properties = None
        else:
                names = list (set (names).difference (properties))
        e.xml_children = [
                presto.presto_xml (instance, walked), # walked)),
                presto.presto_xml (names, walked)
                ]
        if properties:
                e.xml_children.append (presto.presto_xml (dict ([
                        (n, instance.__dict__.get (n)) for n in properties
                        ]), walked))
        # self.presto_prompt_env['__builtins__'] = None
        return e
        
        
def presto_prompt_async (self, reactor):
        # 1. setup the interpreter environement
        #
        self.presto_prompt_line = reactor.presto_vector.get (u'prompt')
        if self.presto_prompt_env == None:
                self.presto_prompt_env = {}
        self.presto_prompt_env['xdir'] = (
                lambda x=NONE, s=self:presto_xdir (s, x)
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
        method, result = prompt.python_prompt (
                self.presto_prompt_line, self.presto_prompt_env
                )
        # remove any references to the instance and the reactor from
        # the prompt environnement (and xdir is one!)
        #
        del self.presto_prompt_env['xdir']
        del self.presto_prompt_env['self']
        del self.presto_prompt_env['reactor']
        try:
                # make sure the _ reference is deleted from the
                # eval/exec __builtins__ dictionnary ...
                #
                del self.presto_prompt_env['__builtins__']['_']
        except:
                pass
        #
        # 3. either pass a XML element, a producer, or the Python
        # instance presto_xml string as a result. Note that None
        # simply result in an empty element and that this reactor
        # cannot be considered as a valid producer!
        #
        if method == 'excp':
                result = presto.presto_xml (result, set ()) # walked))
        elif hasattr (result, 'xml_name') or (
                result != reactor and hasattr (result, 'more')
                ):
                e = xml_dom.XML_element (u'http://presto/ %s' % method, None)
                e.xml_children = [result]
                return e
                
        elif self.presto_prompt_env.has_key ('__builtins__'):
                result = presto.presto_xml (result, set ())
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
        source = reactor.presto_vector.get (u'prompt')
        if not source:
                reactor ('<presto:presto xmlns:presto="http://presto/" />')
                reactor ('')
                return
        
        try:        
                env = self.presto_prompt_env.copy () # not thread-safe!
        except:
                env = {}
        env['reactor']= reactor
        env['self'] = self
        method, result = prompt.python_prompt (source, env)
        reactor ('<presto:%s xmlns:presto="http://presto/">' % method)
        reactor (presto.presto_xml (result, set ()))
        reactor ('</presto:%s>' % method)
        reactor ('')

presto_prompt_synchronized = presto.presto_synchronize (
        presto_prompt_sync
        )

def presto_debug_async (Debug):
        Debug.presto_prompt_env = None
        # Debug.presto_prompt_async = presto_prompt_async
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
        # Debug.presto_prompt_sync = presto_prompt_sync
        Debug.presto_methods[u'sync'] = presto_prompt_synchronized


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
#        self.xml_dom = reactor.presto_dom
#
# and create a circular link between the DOM instance and its root element.
