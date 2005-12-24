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

"Marginal improvement over Greg Stein's qp_xml.py XML parser"

import weakref

try:
        import pyexpat
except ImportError:
        from xml.parsers import pyexpat
        
        
class XML_element (object):
        
        "The simplest Python implementation of the XML interfaces"

        xml_name = u'namespace tag'
        
        xml_valid = xml_parent = xml_attributes = \
                xml_first = xml_children = xml_follow = None
        

class XML_sparse (object):

        xml_name = xml_parent = xml_attributes = \
                xml_first = xml_children = xml_follow = None
        
        def xml_valid (self, dom):
                parent = dom.xml_parsed
                if parent == None:
                        return # do not fold a root element!
                        
                parent.xml_children.pop ()
                if self.xml_first:
                        if parent.xml_children:
                                prev = parent.xml_children[-1]
                                if prev.xml_follow:
                                        prev.xml_follow += self.xml_first
                                else:
                                        prev.xml_follow = self.xml_first
                        elif parent.xml_first:
                                parent.xml_first += self.xml_first
                        else:
                                parent.xml_first = self.xml_first
                if self.xml_children:
                        parent.xml_children.extend (
                                self.xml_children
                                )
                        parent = self.xml_parent
                        for child in self.xml_children:
                                child.xml_parent = parent
        
class XML_dom (object):
        
        # This class is a prototype for a C type that provides an optimized
        # interface for asynchronous object-oriented XML parser. Practically
        # it implements a sparse tree builder and a single event parser.

        xml_type = XML_element
        xml_types = {}
        xml_unicoding = 1
        xml_expat = xml_parsed = None

        def __init__ (self, xml_prefixes=None, xml_pi=None):
                self.xml_prefixes = xml_prefixes or {}
                self.xml_pi = xml_pi or {}

        def xml_parse (self, input):
                self.xml_parser_reset ()
                t = type (input)
                if t == str:
                        return self.xml_parse_string (input)

                return self.xml_parse_more (input)

        def xml_parse_file (self, file, BLOCKSIZE=4096):
                def more ():
                        return file.read (BLOCKSIZE)
                        
                return self.xml_parse_more (more)

        def xml_parse_more (self, more):
                while True:
                        data = more ()
                        if data == '':
                                break
                                
                        if not self.xml_parse_string (data, 0):
                                return None
                                
                return self.xml_parse_string ('', 1)

        def xml_parse_string (self, input, all=1):
                try:
                        self.xml_expat.Parse (input, all)
                except pyexpat.ExpatError, error:
                        self.xml_parse_error (error)
                        all = 1
                if all:
                        # finished clean up and return the root, let the 
                        # accessor decides what he wants to do with the
                        # elements tree.
                        #
                        e = self.xml_root
                        self.xml_root = None
                        self.xml_expat = self.xml_parsed = None
                        return e
                        
                return True
                #
                # returns the xml_root element, or None when an error occured
                # or True to continue ...

        def xml_parse_error (self, error):
                self.xml_error = error
                while self.xml_parsed != None:
                        self.xml_expat_END (self.xml_parsed.xml_name)
                #
                # validate the XML Document Object Model as much as possible

        def xml_parser_reset (self):
                self.xml_root = self.xml_error = self.xml_parsed = None
                self.xml_expat = pyexpat.ParserCreate (None, ' ')
                self.xml_expat.returns_unicode = self.xml_unicoding
                self.xml_expat.buffer_text = 1
                self.xml_expat.ProcessingInstructionHandler = self.xml_expat_PI
                self.xml_expat.StartNamespaceDeclHandler = self.xml_expat_STARTNS
                self.xml_expat.StartElementHandler = self.xml_expat_START
                self.xml_expat.EndElementHandler = self.xml_expat_END
                self.xml_expat.CharacterDataHandler = self.xml_expat_CDATA

        def xml_expat_PI (self, target, cdata):
                self.xml_pi.setdefault (target, []).append (cdata)

        def xml_expat_STARTNS (self, prefix, uri):
                if not self.xml_prefixes.has_key (uri):
                        self.xml_prefixes[uri] = prefix

        def xml_expat_START (self, name, attributes):
                e = self.xml_types.get (name, self.xml_type) ()
                if name != e.xml_name:
                        e.xml_name = name
                if attributes:
                        if e.xml_attributes:
                                attributes.update (e.xml_attributes)
                        e.xml_attributes = attributes
                e.xml_parent = parent = self.xml_parsed
                if parent == None:
                        self.xml_root = e
                elif parent.xml_children:
                        parent.xml_children.append (e)
                else:
                        parent.xml_children = [e]
                self.xml_parsed = e
                
        def xml_expat_END (self, tag):
                e = self.xml_parsed
                parent = self.xml_parsed = e.xml_parent
                if parent:
                        e.xml_parent = weakref.ref (parent)
                        #
                        # replace the circular reference by None or a 
                        # weak one, making the whole tree "dangle" from
                        # its root and collectable as garbage once the
                        # root is dereferenced.
                if e.xml_valid != None:
                        e.xml_valid (self) # the single event

        def xml_expat_CDATA (self, cdata):
                try:
                        self.xml_parsed.xml_children[-1].xml_follow = cdata
                except:
                        self.xml_parsed.xml_first = cdata

        # The XML_dom instance hosts a "sparse" expat parser and holds the 
        # document's prefixes and processing instructions separately from 
        # the element tree itself.
        #
        # Note that nested XMLNS prefixes are "flattened" at the DOM level.
        # The reason is that nested namespace declaration is usefull to mix
        # arbitrary XML strings in a document without prior knowledge of all
        # prefixes used, yet there is absolutely no need to keep that
        # nesting for a document parsed, or reproduce those nested declaration
        # when serializing the element tree.



# use directly xml_* properties to set element attributes and text
# nodes, and don't bother to do in Python what can be done best in
# XPATH or XSLT. here are two simple and usefull walkers, if you
# need to walk a large XML tree up and down, use something else than
# a "slow" interpreter ...

def xml_root (e):
        "return the root of the element's tree"
        while e.xml_parent != None:
                e = e.xml_parent ()
        return e


def xml_named (e, tag_or_fqn):
        "iterate over named children"
        assert hasattr (e, 'xml_children')
        for child in e.xml_children:
                if child.xml_name.endswith (tag_or_fqn):
                        yield child
                        
        #return (
        #        child for child in e.xml_children 
        #        if child.xml_name.endswith (tag_or_fqn)
        #        )
                
        
# four usefull methods to update an XML_element tree and make
# sure to leave all its interfaces well implemented and the tree
# well-linked.

def xml_remove (parent, child):
        "remove a child and all its children from its parent"
        assert (
                hasattr (parent, 'xml_children') and 
                child in parent.xml_children
                )
        children = parent.xml_children
        if child.xml_follow:
                index = children.index (child)
                if index == 0:
                        if parent.xml_first:
                                parent.xml_first += child.xml_follow
                        else:
                                parent.xml_first = child.xml_follow
                elif children[index-1].xml_follow:
                        children[index-1].xml_follow += child.xml_follow
                else:
                        children[index-1].xml_follow = child.xml_follow
        children.remove (child)


def xml_delete (e):
        "delete this element and all its children from the tree"
        assert hasattr (e, 'xml_parent') and e.xml_parent != None
        xml_remove (e.xml_parent (), e)
        

def xml_inherit (parent, first, children, follow, index, slice=0):
        "let the parent inherit the orphaned's first, children and follow"
        assert parent.xml_children
        if first:
                if index == 0:
                        if parent.xml_first:
                                parent.xml_first += first
                        else:
                                parent.xml_first = first
                else:
                        parent.xml_children[index-1].xml_follow += first
        for child in children:
                child.xml_parent = parent
        if follow:
                if child.xml_follow:
                        child.xml_follow += follow
                else:
                        child.xml_follow = follow
        if slice == 0 and index == len (parent.xml_children):
                parent.xml_children.extend (children)
        else:
                parent.xml_children = (
                        parent.xml_children[:index] + children +
                        parent.xml_children[index + slice:]
                        )
        #
        # this *is* a practical interface to "flatten" tree in place, 
        # but also "insert" or "paste" selections.


def xml_orphan (e):
        "remove this element and attach its children to its parent"
        assert hasattr (e, 'xml_parent') and e.xml_parent != None
        parent = e.xml_parent ()
        if e.xml_children:
                xml_inherit (
                        parent, e.xml_first, e.xml_children, e.xml_follow, 
                        parent.xml_children.index (e), 1
                        )
        else:
                xml_remove (parent, e)
        

def xml_benchmark (clock, string, xml_types, xml_type, unicoding):
        t = clock ()
        dom = XML_dom ()
        dom.xml_type = xml_type
        dom.xml_types = xml_types
        dom.xml_unicoding = unicoding
        dom.xml_parser_reset ()
        root = dom.xml_parse_string (string)
        return (root, dom, clock () - t)


if __name__ == '__main__':
        import sys, os, time
        sys.stderr.write (
                'Allegra XML/DOM'
                ' - Copyright 2005 Laurent A.V. Szyster'
                ' | Coypleft GPL 2.0\n'
                )
        if os.name == 'nt':
                clock = time.clock
        else:
                clock = time.time
        unicoding = 1
        if len (sys.argv) > 1:
                if sys.argv[1] == 'UTF-8':
                        unicoding = 0
        s = sys.stdin.read ()
        root, dom, seconds =  xml_benchmark (
                clock, s, {}, XML_sparse, unicoding
                )
        if root == None:
                sys.sdterr.write (dom.xml_error + '\n')
        sys.stderr.write ('parsed in %f sec\n' % seconds)
        
        
# Note about this implementation
#
# The xml_dom.py module is a thin layer around Python's expat bindings, 
# designed to support the developpement of non-blocking, object-oriented
# XML processors.
#
# This module delivers a few marginal improvements from Greg Stein's
# original work: 1) a consistent name space, without possible conflicts
# with the many different applications of XML; 2) element type declaration
# and validation interfaces, a new point of articulation for developpers 
# that enables a new kind of XML processor design; 
#
#
# Two New Simple Interfaces
#
# Here is the synopsis of xml_dom's interfaces
#
# >>> from allegra import xml_dom
# >>> class XML_tag (xml_dom.XML_element): pass
# >>> dom = xml_dom.XML_dom ({u'tag': XML_tag})
# >>> root = dom.xml_parse (
# ...    '<tag name="value">first '
# ...    '<schmarkup>...</schmarkup> follow</tag>'
# ...    )
# >>> root.xml_name
# u'tag'
# >>> root.xml_first
# u'first ... follow'
# >>> root.xml_attributes
# {u'name': u'value'}
# >>> root.xml_follow == xml_parent == None
# True
# >>> root.xml_children
# []
#
#
# A Better Optimization Strategy: 
#
# I'm too lazy to loose focus on the context, and I did not forget my
# benchmarks of expat: when parsing, the Python interface will cost nothing
# until event handlers are registered then called-back, and it gets much
# worse when object are instanciated. cElementTree is *so* close to expat
# in the effbot's benchmark, but only because it "does" nothing really
# usefull besides moving XML from a string into a memory tree.
#
# If you *need* to program your XML processing in Python rather than in 
# XSLT, then you will probably end up instanciating specialized objects 
# for many tags, paying the full price on top of the time allready spent
# to create the cElement instance (however lite).
#
# It may sound vain to make such big claim before having even started the
# optimization process, but I have had some experience with Python, expat
# and various high profile XML libraries. As far as Python is concerned,
# qp_xml.py still was my favorite base for developping XML processors. 
#
# Looking deeper into celementtree C source, considering the need for an
# iterparse interface overwhelmed its performance cost and yet its inability
# to provide a better parser interface than expat, I'm quite satisfied to
# have stayed quietly close to qp_xml.py original design and true to my
# first intuition.
#
# object-oriented XML parsers are cool ... and they can be fast too.
#
# Here is the "hack to-do":
#
# 1. instanciate new objects from the C parser loop for element names
#    indexed, using the mapped XML element class
#
# 2. or use a default type, by default an ad-hoc C type
#
# 3. when no default type is provided, simply drop non-matching markup
#    and buffer the CDATA marked up.
#
# This is an interface optimized for the simple folling case:
#
#        root = XML_dom ({u'tag': XML_class}).xml_parse ('<?xml ...')
#
# "hide" anything other markup than <tag/>, only call 
#
#        XML_class.xml_valid (self, dom)
#
# for each valid element and drop the schmarkup you don't care about.
# Yet another application is to specify a class with no __new__, __init__
# or xml_valid method and with __slots__ only for the xml_* namespace:
#
#         root = XML_dom (
#                {u'tag': XML_class}, XML_element
#                ).xml_parse ('<?xml ...')
#
# for which the C parser can be optimized.
#  
# The result would be a fast "sparse" parser, a fast "sparse" tree-maker,
# with the most practical interface available to develop extensible, object
# oriented and yet buffering XML processor like the PNS/XML articulator.
# 
# Combined with a C implementation of xml_unicode and xml_utf8 (they are
# quite stable now), an eventual xml_c modules will deliver performances
# not worse than celementtree when applied. Globbing a megabyte long and
# deep XML documents in memory will allways be faster with celementtree,
# but a simpler Allegra XML parser will "iter" through that same megabyte
# and process at a marginally greater speed if some of its markup can be
# dropped.
#
#
# Lesson
#
# Practically, the lesson of all the wandering around XML in Python (from
# qp_xml.py, pyexpat, a full SIG, then bloatware, then back to qp_xml.py
# via ElementTree and finally back to square zero with the so much needed 
# iterparse interface), is that people don't benchmark the basics and forget
# easely their context.
#
# Python is made to integrate, prototype and test C libraries. It is a very
# powerfull application language because those three functions are the bread
# and butter of software developpers. But CPython is not a fast language.
#
# Notably, it is terribly slow at two articulations: interpreter call-back
# and object instanciation.
#
# As Python packages and modules, the 4XML suite and even celementtree are
# out of context. The first one should be (and is, but by others) written
# in C and then wrapped for Python. The second one, although close, does 
# not provide a new point of articulation not yet made available by expat
# itself: it is a fast but indiscriminate tree-maker that only has
# an after-though iteration interface to develop parsers, it is a specialized
# version of expat.

