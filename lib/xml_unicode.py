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
        if name.find (u' ') < 0:
                return name

        return name.split (u' ')[1]

def xml_attr (data, encoding='ASCII'):
        assert type (data) == types.UnicodeType
        data = data.replace (u"&", u"&amp;")
        data = data.replace (u"\"", u"&quot;")
        data = data.replace (u"<", u"&lt;")
        data = data.replace (u"\t", u"&#x9;")
        data = data.replace (u"\r", u"&#xD;")
        data = data.replace (u"\n", u"&#xA;")
        return data.encode (encoding, 'xmlcharrefreplace')

def xml_cdata (data, encoding='ASCII'):
        assert type (data) == types.UnicodeType
        data = data.replace (u"&", u"&amp;")
        data = data.replace (u"<", u"&lt;")
        data = data.replace (u">", u"&gt;")
        return data.encode (encoding, 'xmlcharrefreplace')

                                        
def xml_ns (prefixes, encoding='ASCII'):
        s = ''
        for uri, prefix in prefixes.items ():
                if uri == u'http://www.w3.org/XML/1998/namespace':
                        continue
                
                if prefix:
                        s += ' xmlns:%s="%s"' % (
                                prefix.encode (encoding, 'xmlcharrefreplace'),
                                xml_attr (uri, encoding)
                                )
                else:
                        s += ' xmlns="%s"' % xml_attr (uri, encoding)
        return s


def xml_auto_prefix (prefixes):
        i = 0
        while prefixes.has_key (u'ns%d' % i):
                i += 1                
        return u'ns%d' % i
        

def xml_prefix_FQN (name, prefixes, encoding='ASCII'):
        try:
                ns, name = name.split (u' ')
        except:
                return name.encode (encoding, 'xmlcharrefreplace'), ''
        
        prefix = prefixes.get (ns, 0)
        if prefix:
                return '%s:%s' % (
                        prefix.encode (encoding, 'xmlcharrefreplace'),
                        name.encode (encoding, 'xmlcharrefreplace')
                        ), ''
        
        if prefix == None:
                return name.encode (encoding, 'xmlcharrefreplace'), ''
        
        prefix = xml_auto_prefix (prefixes).encode (
                encoding, 'xmlcharrefreplace'
                )
        return '%s:%s' % (
                prefix, name.encode (encoding, 'xmlcharrefreplace')
                ), ' xmlns:%s="%s"' % (
                        prefix, xml_attr (ns, encoding)
                        )


def xml_prefix_FQN_attribute (name, value, prefixes, encoding='ASCII'):
        try:
                ns, name = name.split (u' ')
        except:
                return ' %s="%s"' % (
                        name.encode (encoding, 'xmlcharrefreplace'),
                        xml_attr (value, encoding)
                        )
        
        if prefixes.has_key (ns):
                return ' %s:%s="%s"' % (
                        prefixes[ns].encode (encoding, 'xmlcharrefreplace'), 
                        name.encode (encoding, 'xmlcharrefreplace'),
                        xml_attr (value, encoding)
                        )
        
        else:
                prefix = xml_auto_prefix (prefixes).encode (
                        encoding, 'xmlcharrefreplace'
                        )
                return ' %s:%s="%s" xmlns:%s="%s"' % (
                        prefix, name.encode (encoding, 'xmlcharrefreplace'),
                        xml_attr (value, encoding),
                        prefix, xml_attr (ns, encoding)
                        )


def xml_cdatas (e, encoding='ASCII'):
        if e.xml_first:
                yield e.xml_first.encode (encoding)
                
        if e.xml_children:
                for child in e.xml_children:
                        if hasattr (child, 'xml_name'):
                                for s in xml_cdatas (child, encoding):
                                        yield s
                                        
                                if child.xml_follow:
                                        yield child.xml_follow.encode (
                                                encoding
                                                )
                                

def xml_unprefixed (e, xml_attributes='', encoding='ASCII'):
        if e.xml_name.find (' ') < 0:
                tag = e.xml_name.encode (encoding)
        else:
                tag = e.xml_name.split (u' ')[1].xml_name.encode (encoding)
        if e.xml_attributes:
                xml_attributes = ''.join ((
                        ' %s="%s"' % (
                                name.encode (encoding, 'xmlcharrefreplace'), 
                                xml_attr (value, encoding))
                        for name, value in e.xml_attributes.items ()
                        ))
        if e.xml_children:
                if e.xml_first:
                        yield '<%s%s>%s' % (
                                tag, xml_attributes,
                                xml_cdata (e.xml_first, encoding)
                                )
                
                else:        
                        yield '<%s%s>' % (tag, xml_attributes)
                        
                for child in e.xml_children:
                        if hasattr (child, 'xml_name'):
                                for s in xml_unprefixed (child, '', encoding):
                                        yield s
                        
                                if child.xml_follow:
                                        yield xml_cdata (
                                                child.xml_follow, encoding
                                                )
                        
                        elif type (child) == types.UnicodeType:
                                yield xml_cdata (child, encoding)
                                
                        else:
                                yield child
                                
                yield '</%s>' % tag
                
        elif e.xml_first:
                yield '<%s%s>%s</%s>' % (
                        tag, xml_attributes,
                        xml_cdata (e.xml_first, encoding), tag
                        )
        else:
                yield '<%s%s />' % (tag, xml_attributes)
                

def xml_prefixed (e, prefixes, xml_attributes='', encoding='ASCII'):
        tag, xmlns = xml_prefix_FQN (e.xml_name, prefixes, encoding)
        if e.xml_attributes:
                xml_attributes += xmlns + ''.join ((
                        xml_prefix_FQN_attribute (
                                name, value, prefixes, encoding
                                )
                        for name, value in e.xml_attributes.items ()
                        ))
        if e.xml_children:
                if e.xml_first:
                        yield '<%s%s>%s' % (
                                tag, xml_attributes, 
                                xml_cdata (e.xml_first, encoding)
                                )
                                
                else:
                        yield '<%s%s>' % (tag, xml_attributes)
                                
                for child in e.xml_children:
                        if hasattr (child, 'xml_name'):
                                for s in xml_prefixed (
                                        child, prefixes, '', encoding
                                        ):
                                        yield s
                        
                                if child.xml_follow:
                                        yield xml_cdata (
                                                child.xml_follow, encoding
                                                )
                        
                        elif type (child) == types.UnicodeType:
                                yield xml_cdata (child, encoding)
                                
                        else:
                                yield child
                                
                yield '</%s>' % tag
                
        elif e.xml_first:
                yield '<%s%s>%s</%s>' % (
                        tag, xml_attributes,
                        xml_cdata (e.xml_first, encoding), tag
                        )
                        
        else:
                yield '<%s%s />' % (tag, xml_attributes)
                         

def xml_pi (processing_instructions, encoding='ASCII', delimiter=''):
        return delimiter.join ((
                delimiter.join (('<?%s %s?>' % (
                        pi[0].encode (encoding, 'xml_charrefreplace'),
                        cdata.encode (encoding, 'xml_charrefreplace')
                        ) for cdata in pi[1]))
                for pi in processing_instructions.items ()
                ))


def xml_string (root, prefixes, encoding='ASCII', delimiter=''):
        if prefixes == None:
                return delimiter.join (xml_unprefixed (root, encoding))
                
        return delimiter.join (xml_prefixed (
                root, prefixes, xml_ns (prefixes, encoding), encoding
                ))


def xml_document (
        dom, encoding='ASCII', delimiter='', 
        head='<?xml version="1.0" encoding="%s"?>\r\n'
        ):
        if dom.xml_pi:
                head = delimiter.join ((
                        head % encoding, xml_pi (dom.xml_pi, encoding)
                        ))
        else:
                head = head % encoding
        return delimiter.join ((
                head, xml_string (
                        dom.xml_root, dom.xml_prefixes, encoding, delimiter
                        )
                ))


def xml_valid (encoded, prefixes=None, encoding='ASCII'):
        dom = xml_dom.parse_string (encoded)
        if dom.xml_root:
                if prefixes:
                        dom.xml_prefixes.update (prefixes)
                return xml_prefixed (dom.xml_root, dom.xml_prefixes, xml_ns (
                        dom.xml_prefixes, encoding
                        ), encoding)
        
        return ()


class XML_static (object):
        
        xml_name = xml_parent = xml_attributes = \
                xml_first = xml_children = xml_follow = None

        xml_encoding = 'ASCII'
        
        def xml_valid (self, dom):
                if self.xml_parent == None:
                        return
                
                parent = self.xml_parent ()
                prefixes = dom.xml_prefixes
                if type (parent) == XML_static:
                        parent.xml_children[-1] = ''.join (xml_prefixed (
                                self, prefixes, '', self.xml_encoding
                                ))
                else:
                        parent.xml_children[-1] = ''.join (xml_prefixed (
                                self, prefixes, xml_ns (
                                        prefixes, self.xml_encoding
                                        ), self.xml_encoding
                                ))


if __name__ == '__main__':
        import os, sys, time
        sys.stderr.write (
                'Allegra XML/UNICODE Validator'
                ' - Copyright 2005 Laurent A.V. Szyster\n'
                )
        if os.name == 'nt':
                allegra_time = time.clock
        else:
                allegra_time = time.time
        if len (sys.argv) > 1:
                encoding = sys.argv[1]
        else:
                encoding = 'ASCII'
        def more ():
                return sys.stdin.read (4096)
        t_parse = allegra_time ()
        dom = xml_dom.parse_more (more)
        t_parsed = allegra_time () - t_parse
        sys.stderr.write ('loaded in %f sec\n\n' % t_parsed)
        if dom.xml_root != None:
                t_serialize = allegra_time () 
                data = xml_document (dom.xml_root, dom, encoding)
                t_serialized = allegra_time () - t_serialize
                sys.stdout.write (data)
                sys.stderr.write ('\n\nserialized in %f sec\n' % t_serialized)
        if dom.xml_error:
                sys.stderr.write ('%s\n' % dom.xml_error)
                
                
# Note about this implementation
#
# This is, quite litteraly, a transcription of the interfaces and algorithms
# found in xml_utf8.py but for an UNICODE output of the XML parser.
#
# It is about 50% slower than the "pure" UTF-8 implementation, but
# there are very good reasons to support UNICODE inside the Python VM and
# be able to communicate with various encoding. Not all consoles, pipes,
# or browser will support UTF-8. There are 7bit applications and cp437 
# charsets out there ...