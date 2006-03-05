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

from xml.parsers import expat
        

class XML_element (object):
        
        "The simplest ELEMENT type possible"

        def __init__ (self, name, attributes):
                if name != self.xml_name:
                        self.xml_name = name
                if attributes:
                        self.xml_attributes = attributes
                
        xml_valid = xml_parent = xml_name = xml_attributes = \
                xml_first = xml_children = xml_follow = None
        

class XML_delete (object):
        
        "An element that drops itself from the XML tree"

        def __init__ (self, name, attributes):
                pass

        xml_name = xml_parent = xml_attributes = \
                xml_first = xml_children = xml_follow = None
                
        def xml_valid (self, dom): 
                parent = dom.xml_parsed
                if parent == None:
                        return # do not drop a root element!
                        
                parent.xml_children.pop ()


def xml_sparse (self, dom):
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

class XML_sparse (object):
        
        "A sparse element that folds itself from the tree, preserves CDATA"

        def __init__ (self, name, attributes):
                pass

        xml_name = xml_parent = xml_attributes = \
                xml_first = xml_children = xml_follow = None

        xml_valid = xml_sparse        
        

class XML_dom (object):
        
        "The DOM interface to the standard expat event-driven parser"

        xml_type = XML_element
        xml_types = {}
        xml_unicoding = 1
        xml_expat = xml_parsed = xml_error = None

        def __init__ (self, prefixes=None, pi=None):
                self.xml_prefixes = prefixes or {}
                self.xml_pi = pi or {}

        def xml_parser_reset (self):
                if self.xml_unicoding:
                        self.xml_first = u''
                else:
                        self.xml_first = ''
                self.xml_root = self.xml_error = self.xml_parsed = None
                self.xml_expat = parser = expat.ParserCreate (None, ' ')
                parser.returns_unicode = self.xml_unicoding
                parser.buffer_text = 1
                parser.StartElementHandler = self.xml_expat_START
                parser.EndElementHandler = self.xml_expat_END
                parser.CharacterDataHandler = self.xml_expat_CDATA
                if self.xml_pi != None:
                        parser.ProcessingInstructionHandler = \
                                self.xml_expat_PI
                if self.xml_prefixes != None:
                        parser.StartNamespaceDeclHandler = \
                                self.xml_expat_STARTNS

        def xml_expat_PI (self, target, cdata):
                self.xml_pi.setdefault (target, []).append (cdata)

        def xml_expat_STARTNS (self, prefix, uri):
                if not self.xml_prefixes.has_key (uri):
                        self.xml_prefixes[uri] = prefix

        def xml_expat_START (self, name, attributes):
                e = self.xml_types.get (name, self.xml_type) (
                        name, attributes
                        )
                e.xml_parent = parent = self.xml_parsed
                e.xml_first = self.xml_first
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
                        #
                        # there are children, this must be following cdata.
                except:
                        self.xml_parsed.xml_first += cdata
                        #
                        # either this is the first cdata, or some sparse 
                        # or deleted elements must have been removed from
                        # the tree.

        def xml_expat_ERROR (self, error):
                self.xml_error = error
                while self.xml_parsed != None:
                        self.xml_expat_END (self.xml_parsed.xml_name)
        
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


def parse_string (data, DOM=XML_dom, unicoding=1):
        if unicoding:
                dom = DOM ({u'http://www.w3.org/XML/1998/namespace': u'xml'})
        else:
                dom = DOM ({'http://www.w3.org/XML/1998/namespace': 'xml'})
        dom.xml_unicoding = unicoding
        dom.xml_parser_reset ()
        try:
                dom.xml_expat.Parse (data, 1)
        except expat.ExpatError, error:
                dom.xml_expat_ERROR (error)
        dom.xml_expat = None
        return dom


def parse_more (more, DOM=XML_dom, unicoding=1):
        if unicoding:
                dom = DOM ({u'http://www.w3.org/XML/1998/namespace': u'xml'})
        else:
                dom = DOM ({'http://www.w3.org/XML/1998/namespace': 'xml'})
        dom.xml_unicoding = unicoding
        dom.xml_parser_reset ()
        try:
                data = more ()
                while data:
                        dom.xml_expat.Parse (data, 0)
                dom.xml_expat.Parse ('', 1)
        except expat.ExpatError, error:
                dom.xml_expat_ERROR (error)
        dom.xml_expat = None
        return dom


# A few DOM manipulations
#
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
        

if __name__ == '__main__':
        def benchmark (clock, string, DOM, unicoding):
                t = clock ()
                dom = parse_string (string, DOM, unicoding)
                return (dom, clock () - t)
        
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
        dom, seconds =  benchmark (clock, s, XML_dom, unicoding)
        if dom.xml_error != None:
                sys.stderr.write (dom.xml_error + '\n')
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
# SYNOPSIS
#
# >>> from allegra import xml_dom
# >>> xml_dom.XML_dom.xml_types = {u'schmarkup': xml_dom.XML_sparse}
# >>> dom = xml_dom.parse_string (
# ...    '<tag name="value">first '
# ...    '<schmarkup>...</schmarkup> '
# ...    'follow</tag>'
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
