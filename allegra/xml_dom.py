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

"my own version of Greg Stein's qp_xml.py original XML object model"

from types import StringTypes
from weakref import ref
try:
        import pyexpat
except ImportError:
        from xml.parsers import pyexpat


class XML_element:
        
        "the simplest XML element interface implementation"

        xml_name = u'namespace tag'
        
        xml_parent = None
        xml_attributes = None
        xml_first = None
        xml_children = None
        xml_follow = None
        
        def xml_valid (self, dom):
                pass # to subclass
        

# five usefull methods to manipulate an XML_element tree and make
# sure to leave all its interfaces well implemented and the tree
# well-linked.
#
# use directly xml_* properties to set element attributes and text
# nodes, and don't bother to do in Python what can be done best in
# XPATH or XSLT.
#

def xml_root (e):
        "return the root of the element's tree"
        while e.xml_parent != None:
                e = e.xml_parent ()
        return e


def xml_named (e, tag_or_fqn):
        "iterates over named children"
        for child in e.xml_children:
                if child.xml_name.endswith (tag_or_fqn):
                        yield child
        
        
def xml_remove (e, child):
        "remove a child and all its children from this element"
        assert hasattr (e, 'xml_children') and child in e.xml_children
        if child.xml_follow:
                index = e.xml_children.index (child)
                if index == 0:
                        if e.xml_first:
                                e.xml_first += child.xml_follow
                        else:
                                e.xml_first = child.xml_follow
                elif e.xml_children[index-1].xml_follow:
                        e.xml_children[index-1].xml_follow += child.xml_follow
                else:
                        e.xml_children[index-1].xml_follow = child.xml_follow
        e.xml_children.remove (child)


def xml_delete (e):
        "delete this element and all its children from the tree"
        assert hasattr (e, 'xml_parent') and e.xml_parent != None
        xml_remove (e.xml_parent (), e)
        

def xml_orphan (e):
        "remove this element and attach its children to its parent"
        assert hasattr (e, 'xml_parent') and e.xml_parent != None
        if not e.xml_children:
                xml_remove (e.xml_parent (), e)
                return
                
        parent = e.xml_parent ()
        index = parent.xml_children.index (e)
        for child in e.xml_children:
                if hasattr (child, 'xml_parent'):
                        child.xml_parent = e.xml_parent
        if e.xml_follow:
                if child.xml_follow:
                        child.xml_follow += e.xml_follow
                else:
                        child.xml_follow = e.xml_follow
        parent.xml_children = (
                parent.xml_children[:index] + 
                e.xml_children +
                parent.xml_children[index+1:]
                )
        del e.xml_parent


class XML_dom:
        
        # TODO: support more expat interfaces ...
        
        xml_class = XML_element
        xml_classes = {}
        xml_unicoding = 1

        def __init__ (self, xml_prefixes=None, xml_pi=None):
                self.xml_prefixes = xml_prefixes or {}
                self.xml_pi = xml_pi or {}

        def xml_parser_reset (self):
                self.xml_root = self.xml_error = self._curr = None
                self.xml_expat = pyexpat.ParserCreate (None, ' ')
                self.xml_expat.returns_unicode = self.xml_unicoding
                self.xml_expat.buffer_text = 1
                self.xml_expat.ProcessingInstructionHandler = self.xml_expat_PI
                self.xml_expat.StartNamespaceDeclHandler = self.xml_expat_STARTNS
                self.xml_expat.StartElementHandler = self.xml_expat_START
                self.xml_expat.EndElementHandler = self.xml_expat_END
                self.xml_expat.CharacterDataHandler = self.xml_expat_CDATA
                
        def xml_parse_string (self, input, all=1):
                try:
                        self.xml_expat.Parse (input, all)
                except pyexpat.ExpatError, error:
                        # save the error message
                        self.xml_parse_error (error)
                        all = 1
                if all:
                        # finished without error, clean up and return the
                        # root, let the accessor decides what he wants to
                        # do with that tree.
                        e = self.xml_root
                        self.xml_root = self._curr = None
                        del self.xml_expat
                        return e
                        
                return
                #
                # returns the xml_root element or None or 1 to continue

        def xml_parse_file (self, input, BLOCKSIZE=4096):
                data = input.read (BLOCKSIZE)
                while data:
                        error = self.xml_parse_string (data, 0)
                        if error:
                                return error

                        data = input.read (BLOCKSIZE)
                return self.xml_parse_string ('', 1)

        def xml_parse_error (self, error):
                self.xml_error = error
                while self._curr != None:
                        self.xml_expat_END (self._curr.xml_name)
                #
                # validate the XML Document Object Model as much as possible

        # TODO: move the expat callback interfaces to a C thin wrapper
        #       around expat itself in order to gain *some* performance
        #       when parsing XML and get a fast validator without Python
        #       callbacks or instanciations at all.

        def xml_expat_PI (self, target, cdata):
                self.xml_pi.setdefault (target, []).append (cdata)

        def xml_expat_STARTNS (self, prefix, uri):
                if not self.xml_prefixes.has_key (uri):
                        self.xml_prefixes[uri] = prefix

        def xml_expat_START (self, name, attributes):
                e =  self.xml_classes.get (name, self.xml_class) ()
                if attributes:
                        if e.xml_attributes:
                                attributes.update (e.xml_attributes)
                        e.xml_attributes = attributes
                if name != e.xml_name:
                        e.xml_name = name
                parent = self._curr
                if parent == None:
                        self.xml_root = e
                else:
                        if parent.xml_children:
                                parent.xml_children.append (e)
                        else:
                                parent.xml_children = [e]
                e.xml_parent = self._curr
                self._curr = e
                
        def xml_expat_END (self, tag):
                e = self._curr
                parent = self._curr = e.xml_parent
                if parent:
                        e.xml_parent = ref (parent)
                        # replace the circular reference by a weak one
                        # making the whole tree dangling from the root
                        # and easy to collect as garbage.
                e.xml_valid (self)

        def xml_expat_CDATA (self, cdata):
                e = self._curr
                if e.xml_children:
                        e.xml_children[-1].xml_follow = cdata
                else:
                        e.xml_first = cdata

        # The purpose of XML_dom instance is to host an expat parser and
        # carry on the document's prefixes and processing instructions
        # separately from the element tree itself.
        #
        # Note that nested XMLNS prefixes are "flattened" at the DOM level.
        # The reason is that nested namespace declaration is usefull to mix
        # arbitrary XML strings in a document without prior knowledge of all
        # prefixes used, yet there is absolutely no need to keep that
        # nesting for a document parsed, or reproduce those nested declaration
        # when serializing the element tree.


if __name__ == '__main__':
        import os, sys, time
        if os.name == 'nt':
                allegra_time = time.clock
        else:
                allegra_time = time.time
        sys.stderr.write (
                'Allegra XML/DOM'
                ' - Copyright 2005 Laurent A.V. Szyster'
                ' | Coypleft GPL 2.0\n'
                )
        unicoding = 1
        if len (sys.argv) > 1:
                if sys.argv[1] == 'UTF-8':
                        unicoding = 0
        t = allegra_time ()
        dom = XML_dom ()
        dom.xml_unicoding = unicoding
        dom.xml_parser_reset ()
        root = dom.xml_parse_file (sys.stdin)
        t = allegra_time () - t
        if root == None:
                sys.sdterr.write (dom.xml_error + '\n')
        sys.stderr.write ('instanciated in %f sec\n' % t)
                
                
# Note about this implementation
#
# This module is the base for all XML processing in Allegra.
#
# And yes, this is a "slow cow" compared to the similar cElementTree.
#
# However, coming up first with a good interface is a lot more practical in
# Python than in C. The rule is: "measure twice, cut once". Measure twice or
# more the interface with actual applications of it, then optimize its Python
# implementation and finally, a sound interface has settled, speed up its 
# execution with a few C functions.
#
# The xml_dom interfaces have been applied (measure) by enough different
# applications to be reviewed publicly (cut) and its execution may now be
# optimized for each plateform and type of applications.
#
# It took five years, but this Python object model for XML can be applied
# to develop all major applications for which Python is a sensible choice:
#
#        . object-oriented XML user agents
#        . simple persistent XML component interfaces
#        . fast *and* practical asynchronous XML producers
#
# There are of course XML applications that fall in other categories than 
# ad-hoc agents, persistence or I/O. Yet, those are mainly large XML document
# transformation, XML validation against DTD and schemas, and other kind of
# specialised batch/pipe processes that should be developped with a more
# appropriate language/tool (like a browser's XSLT library, an instance of 
# HTMLTidy, Your Mileage May Vary).
#
# So, in the realm of Python applications of XML, this object model is
# pretty much all I need ;-)
#
#
# The XML_element class
#
# This Python classic class implementation is fast to instanciate (no __init__ 
# or __new__ callback ;-) and has a minimal memory footprint, with default
# class properties for all interfaces.
#
# Note that xml_attributes and xml_children remain class properties for
# elements that have not been assigned their own by the XML_dom parser.
# This allows default attributes and child elements to be set at the
# class level and let different element instances "link" to shared trees
# of XML elements.
#
# This powerfull API is of course also dangerous, because an instance
# method that intends to manipulate the element tree must allway
# check that the presence of an xml_children sequence or an xml_attributes
# mapping.
#
#
# Flexibility of a "loose" Document Object Model
#
# This module implements a very flexible DOM with a remarkable xml_children
# interface put to good use by xml_utf8 and xml_unicode for serialization
# but also by presto. 
# 
# In most practical case, I found that an application generates quite 
# simple XML strings which are faster and easier to sprintf than to 
# serialize from an element tree. Even using the defacto superfast
# cElementTree types, because their accessor functions are in Python.
# 
# When processing XML (like applying XSL transformation or "grepping" a
# huge document for some XPATH) dedicated types or binding xlibs make a
# lot of sense. Not for dumb XML generation from an SQL result, XML
# serialization of Python instances, or whatever type of xmlization of
# data structures your application require.
#
# That's why, xml_uft8, xml_unicode support 8bit and 16bit strings in
# the list of xml_children, which are respectively dumped "as-is" and
# encoded. Moreover, note that this simple design allows PRESTo to supports
# the presence of producers (anything with a 'more' interface) and serializes
# anything else using its own Python instance tree "serialization".
#
#
# Encoding
#
# By default the expat parser used by XML_dom instance produce UNICODE and
# developpers should use xml_unicode.py to serialize an element tree back
# to XML, in a given encoding (or ASCII by default). However, they may as
# well specify to produce UTF-8 and use the equivalent xml_utf8.py
# interfaces to serialize in a UTF-8 encoded XML string.
#
# The purpose of XML_dom is *not* to process large documents but rather
# to instanciate relatively small Python element trees. Using UNICODE as
# a and encoding to ASCII provide a cross-plateform foundation to this
# Python application of XML.
#
#
# Performances
#
# This is not a fast DOM ... yet. It's just a decent way to serialize and
# state as XML documents and build some smarter object oriented parser.
#
# However instances created for each element are lightweight and can - once
# completed - fold themselves or even "fall" from the tree. So it is possible
# to implement reasonably fast parsers with it for relatively short long-lived
# Python instance trees (or Document Object Model) but also memory-savy XML
# pipes with light-weight object-oriented interfaces on which to build modular
# XML "mapper". 
#
# An XML_dom may be fed with very large document without creating other
# scarcity than the cost of callbacks to the interpreter, instanciation
# of a lean classic class, a call to its xml_valid method and subsequent
# finalization of the validated elements. 
#
#
# Optimization
#
# Aside the serialization functions that all beg for C optimization, the
# only way to keep the benefit of the model and gain speed is to wrap the
# parser very thinly, and callback the interpreter only for element 
# with a subsclassed or overloaded xml_init method. But what costs most
# is Python object instanciation itself. For the intended purpose, short
# XML strings to instanciate web objects or concise web document allready
# cleansed from redundant markup to articulate as it is parsed. 
#
# The function xml_valid_string, that produces valid XML from a possibly
# invalid or trunked, XML string, is the perfect candidate for a thin Expat
# wrapper that can be called once, uses a C datastructure for its tree,
# serialize the string as it is parsed and complete it instanciation, if
# only partially invalid.
#
# As far as instanciation, there is pretty much nothing else to do if I
# want to retain the flexibility of mapping XML element names to 
#
#
# XML_dom vs. ElemenTree
#
# Well, the design is the same: the Greg Stein's qpxml.py dating back Y2K.
#
# That unorthodox DOM is the best data structure for genral XML document
# processing. There is one way to do it that keeps the XML implementation
# simple. And that is what XML was designed for in the first place.
#
# As performance is concerned cElemenTree allready optimized and there
# is also no doubt that the ElementTree package covers more ground and API
# that xml_dom. However, there are two distinct features that I like better
# in my way.
#
# First a purely semantic aspect, but that has some significant practical
# implications. The API namespace of xml_dom is qualified and designed to
# be mixed-in with other interfaces. I like flat data structures, specially
# with Python which is relatively slow to instanciate objects (there is a
# price to pay for all that power and reliability).
#
# Second, with Expat integrated and using Greg Stein's design as a mode,
# implementation of an DOM is trivial, and I need one that applied both
# to asynchronous producers and to persistent Python instance serialized
# as XML strings.