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

import types

from allegra import xml_dom


def xml_tag (name):
        if name.find (' ') < 0:
                return name

        return name.split (' ')[1]

def xml_attr (data):
        assert type (data) == types.StringType
        data = data.replace ("&", "&amp;")
        data = data.replace ("'", "&apos;")
        data = data.replace ("\"", "&quot;")
        data = data.replace ("<", "&lt;")
        return data.replace (">", "&gt;")

def xml_cdata (data):
        assert type (data) == types.StringType
        data = data.replace ("&", "&amp;")
        data = data.replace ("<", "&lt;")
        return data.replace (">", "&gt;")

                                        
def xml_ns (prefixes):
        s = ''
        for uri, prefix in prefixes.items ():
                if uri == u'http://www.w3.org/XML/1998/namespace':
                        continue
                
                if prefix:
                        s += ' xmlns:%s="%s"' % ( prefix, xml_attr (uri))
                else:
                        s += ' xmlns="%s"' % xml_attr (uri)
        return s


def xml_auto_prefix (prefixes):
        i = 0
        while prefixes.has_key ('ns%d' % i):
                i += 1                
        return 'ns%d' % i
        

def xml_prefix_FQN (name, prefixes):
        try:
                ns, name = name.split (' ')
        except:
                return name, ''
        
        prefix = prefixes.get (ns, 0)
        if prefix:
                return '%s:%s' % (prefix, name), ''
        
        if prefix == None:
                return name, ''
        
        prefix = xml_auto_prefix (prefixes)
        return '%s:%s' % (prefix, name), ' xmlns:%s="%s"' % (
                prefix, xml_attr (ns)
                )


def xml_prefix_FQN_attribute (name, value, prefixes):
        try:
                ns, name = name.split (' ')
        except:
                return ' %s="%s"' % (name, xml_attr (value))
        
        if prefixes.has_key (ns):
                return ' %s:%s="%s"' % (prefixes[ns], name, xml_attr (value))
        
        else:
                prefix = xml_auto_prefix (prefixes)
                return ' %s:%s="%s" xmlns:%s="%s"' % (
                        prefix, name, xml_attr (value),
                        prefix, xml_attr (ns)
                        )


def xml_cdatas (e):
        if e.xml_first:
                yield e.xml_first
                
        if e.xml_children:
                for child in e.xml_children:
                        if hasattr (child, 'xml_name'):
                                for s in xml_cdatas (child):
                                        yield s
                                        
                                if child.xml_follow:
                                        yield child.xml_follow


def xml_unprefixed (e, xml_attributes=''):
        if e.xml_name.find (' ') < 0:
                tag = e.xml_name
        else:
                tag = e.xml_name.split (' ')[1]
        if e.xml_attributes:
                xml_attributes = ''.join ([
                        ' %s="%s"' % (name, xml_attr (value))
                        for name, value in e.xml_attributes.items ()
                        ])
        if e.xml_children:
                if e.xml_first:
                        yield '<%s%s>%s' % (
                                tag, xml_attributes, xml_cdata (
                                        e.xml_first
                                        )
                                )
                
                else:        
                        yield '<%s%s>' % (tag, xml_attributes)
                        
                        
                for child in e.xml_children:
                        if hasattr (child, 'xml_name'):
                                for s in xml_unprefixed (child):
                                        yield s
                        
                                if child.xml_follow:
                                        yield xml_cdata (child.xml_follow)
                        
                        else:
                                yield child
                                
                yield '</%s>' % tag
                
        elif e.xml_first:
                yield '<%s%s>%s</%s>' % (
                        tag, xml_attributes, xml_cdata (
                                e.xml_first
                                ), tag
                        )
        else:
                yield '<%s%s />' % (tag, xml_attributes)
                

def xml_prefixed (e, prefixes, xml_attributes=''):
        tag, xmlns = xml_prefix_FQN (e.xml_name, prefixes)
        if e.xml_attributes:
                xml_attributes += xmlns + ''.join ([
                        xml_prefix_FQN_attribute (name, value, prefixes)
                        for name, value in e.xml_attributes.items ()
                        ])
        if e.xml_children:
                if e.xml_first:
                        yield '<%s%s>%s' % (
                                tag, xml_attributes, xml_cdata (e.xml_first)
                                )

                else:
                        yield '<%s%s>' % (tag, xml_attributes)
                        
                for child in e.xml_children:
                        if hasattr (child, 'xml_name'):
                                for s in xml_prefixed (child, prefixes):
                                        yield s
                        
                                if child.xml_follow:
                                        yield xml_cdata (child.xml_follow)
                        
                        else:
                                yield child
                                
                yield '</%s>' % tag
                
        elif e.xml_first:
                yield '<%s%s>%s</%s>' % (
                        tag, xml_attributes, xml_cdata (e.xml_first), tag
                        )
                        
        else:
                yield '<%s%s />' % (tag, xml_attributes)
                         

def xml_pi (processing_instructions, delimiter=''):
        return delimiter.join ([
                delimiter.join ([
                        '<?%s %s?>' % (pi[0], cdata) for cdata in pi[1]
                        ])
                for pi in processing_instructions.items ()
                ])
                

def xml_string (root, prefixes, delimiter=''):
        if not prefixes:
                return delimiter.join (list (xml_unprefixed (root)))
                
        return delimiter.join (xml_prefixed (
                root, prefixes, xml_ns (prefixes)
                ))


def xml_document (
        dom, delimiter='', head='<?xml version="1.0" encoding="UTF8"?>'
        ):
        if dom.xml_pi:
                head = delimiter.join ((head, xml_pi (dom.xml_pi)))
        return delimiter.join ((
                head, xml_string (dom.xml_root, dom.xml_prefixes, delimiter)
                ))


def xml_valid (encoded, prefixes=None):
        dom = xml_dom.parse_string (encoded, unicoding=0)
        if dom.xml_root:
                if prefixes:
                        dom.xml_prefixes.update (prefixes)
                return xml_prefixed (dom.xml_root, dom.xml_prefixes)
        
        return ()
                

class XML_static (object):
        
        xml_name = xml_parent = xml_attributes = \
                xml_first = xml_children = xml_follow = None

        def xml_valid (self, dom):
                if self.xml_parent == None:
                        return
                
                prefixes = dom.xml_prefixes
                parent = self.xml_parent ()
                if type (parent) == XML_static:
                        parent.xml_children[-1] = ''.join (
                                xml_prefixed (root, prefixes, '')
                                )
                else:
                        parent.xml_children[-1] = ''.join (xml_prefixed (
                                root, prefixes, xml_ns (prefixes)
                                ))


if __name__ == '__main__':
        import os, sys, time
        sys.stderr.write (
                'Allegra XML/UTF-8 Validator'
                ' - Copyright 2005 Laurent A.V. Szyster\n'
                )
        if os.name == 'nt':
                allegra_time = time.clock
        else:
                allegra_time = time.time
        def more ():
                return sys.stdin.read (4096)
        t_parse = allegra_time ()
        dom = xml_dom.parse_more (more, unicoding=0)
        t_parsed = allegra_time () - t_parse
        sys.stderr.write ('loaded in %f sec:\n\n' % t_parsed)
        if dom.xml_root != None:
                t_serialize = allegra_time () 
                data = xml_document (dom.xml_root, dom)
                t_serialized = allegra_time () - t_serialize
                sys.stdout.write (data)
                sys.stderr.write ('\n\nserialized in %f sec\n' % t_serialized)
        if dom.xml_error:
                sys.stderr.write ('%s\n' % dom.xml_error)
