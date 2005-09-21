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

from types import UnicodeType

from allegra.xml_dom import XML_dom


def xml_tag (name):
        if name.find (u' ') < 0:
                return name

        return name.split (u' ')[1]

def xml_attr (data, encoding='ASCII'):
        assert type (data) == UnicodeType
        data = data.replace (u"&", u"&amp;")
        data = data.replace (u"'", u"&apos;")
        data = data.replace (u"\"", u"&quot;")
        data = data.replace (u"<", u"&lt;")
        data = data.replace (u">", u"&gt;")
        return data.encode (encoding, 'xmlcharrefreplace')

def xml_cdata (data, encoding='ASCII'):
        assert type (data) == UnicodeType
        data = data.replace (u"&", u"&amp;")
        data = data.replace (u"<", u"&lt;")
        data = data.replace (u">", u"&gt;")
        return data.encode (encoding, 'xmlcharrefreplace')

                                        
def xml_ns (prefixes, encoding='ASCII'):
        s = ''
        for uri, prefix in prefixes.items ():
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
                tag = e.xml_name.xml_name.encode (encoding)
        else:
                tag = e.xml_name.split (u' ')[1].xml_name.encode (encoding)
        if e.xml_attributes:
                xml_attributes = ''.join ([
                        ' %s="%s"' % (
                                name.encode (encoding, 'xmlcharrefreplace'), 
                                xml_attr (value, encoding))
                        for name, value in e.xml_attributes.items ()
                        ])
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
                                for s in xml_unprefixed (child, encoding):
                                        yield s
                        
                                if child.xml_follow:
                                        yield xml_cdata (
                                                child.xml_follow, encoding
                                                )
                        
                        elif type (child) == UnicodeType:
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
                xml_attributes += xmlns + ''.join ([
                        xml_prefix_FQN_attribute (
                                name, value, prefixes, encoding
                                )
                        for name, value in e.xml_attributes.items ()
                        ])
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
                        
                        elif type (child) == UnicodeType:
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
        return delimiter.join ([
                delimiter.join (['<?%s %s?>' % (
                        pi[0].encode (encoding, 'xml_charrefreplace'),
                        cdata.encode (encoding, 'xml_charrefreplace')
                        ) for cdata in pi[1]])
                for pi in processing_instructions.items ()
                ])


def xml_string (root, dom, encoding='ASCII', delimiter=''):
        head = '<?xml version="1.0" encoding="%s"?>\n' % encoding
        if dom.xml_pi:
                head += xml_pi (dom.xml_pi, encoding)
        if not dom.xml_prefixes:
                return head + delimiter.join (xml_unprefixed (root, encoding))
                
        return head + delimiter.join (xml_prefixed (
                root, dom.xml_prefixes, xml_ns (
                        dom.xml_prefixes, encoding
                        ), encoding
                ))


def xml_document (
        root, dom, encoding='ASCII', delimiter='', 
        head='<?xml version="1.0" encoding="%s"?>'
        ):
        if dom.xml_pi:
                head = delimiter.join ((
                        head % encoding, xml_pi (dom.xml_pi, encoding)
                        ))
        return delimiter.join ((
                head, xml_string (root, dom.xml_prefixes, encoding, delimiter)
                ))


def xml_valid (encoded, prefixes=None, encoding='ASCII'):
        dom = XML_dom ()
        dom.xml_parser_reset ()
        root = dom.xml_parse_string (encoded)
        if root:
                if prefixes:
                        dom.xml_prefixes.update (prefixes)
                return xml_prefixed (root, dom.xml_prefixes, xml_ns (
                        dom.xml_prefixes, encoding
                        ), encoding)
        
        return ()


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
        t_parse = allegra_time ()
        dom = XML_dom ()
        dom.xml_parser_reset ()
        root = dom.xml_parse_file (sys.stdin)
        t_parsed = allegra_time () - t_parse
        if root == None:
                sys.sdterr.write (dom.xml_error + '\n')
                t_serialized = 0
        else:
                t_serialize = allegra_time () 
                data = '<?xml version="1.0" encoding="%s"?>' % encoding
                if dom.xml_pi:
                        data += xml_pi (dom.xml_pi, encoding)
                sys.stdout.write (data)
                for data in xml_prefixed (
                        root, dom.xml_prefixes, 
                        xml_ns (dom.xml_prefixes, encoding), encoding
                        ):
                        sys.stdout.write (data)
                t_serialized = allegra_time () - t_serialize
        sys.stderr.write (
                'instanciated in %f sec, '
                'serialized in %f sec'
                '\n' % (t_parsed, t_serialized)
                )
                
                
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