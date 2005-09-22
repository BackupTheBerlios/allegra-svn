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
