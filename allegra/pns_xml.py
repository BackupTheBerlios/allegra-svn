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

from allegra.pns_model import pns_name
from allegra.pns_sat import \
        pns_sat_utf8, pns_sat_articulate, \
        SAT_STRIP_UTF8, SAT_SPLIT_UTF8, SAT_ARTICULATE_EN, SAT_RE_WWW
from allegra.xml_dom import \
        XML_dom, XML_element, xml_delete, xml_orphan
        
from allegra import netstring, xml_utf8, xml_unicode                                                


# XML to PNS

class XML_PNS_articulate (XML_element):
        
        # The basic SAT and RE articulator, your mileage may vary ...
        
        pns_context = pns_subject = pns_object = xml_string = ''
        
        sat_re = SAT_RE_WWW
        sat_strip = SAT_STRIP_UTF8
        sat_articulators = SAT_ARTICULATE_EN
        sat_horizon = 126

        pns_articulated = set ()

        def __init__ (self):
                self.pns_horizon = set ()
                self.pns_sats = []
        
        def xml_valid (self, dom):
                self.xml_first = (self.xml_first or '').strip (
                        self.sat_strip
                        )
                if self.xml_parent:
                        self.pns_context = self.xml_parent ().pns_subject
                if self.xml_children and (
                        self.pns_articulate_children (dom) or
                        self.pns_articulate_cdata (dom)
                        ):
                        # let children articulate in the context of this
                        # element's subject ...
                        for child in self.xml_children:
                                child.xml_follow = (
                                        child.xml_follow or ''
                                        ).strip (self.sat_strip)
                                child.pns_articulate (
                                        self.pns_subject, 
                                        self.pns_context or dom.pns_subject, 
                                        dom
                                        )
                        self.xml_string = xml_utf8.xml_string (
                                self, dom.xml_prefixes, ''
                                )
                elif self.pns_articulate_cdata (dom):
                        # self.xml_string = self.xml_first
                        self.xml_string = xml_utf8.xml_string (
                                self, None, ''
                                )
                        self.xml_attributes = None
                self.xml_first = self.xml_children = None
                
        def pns_articulate_children (self, dom):
                if self.xml_children:
                        names = [
                                child.pns_subject 
                                for child in self.xml_children
                                if (
                                        child.pns_subject and 
                                        xml_utf8.xml_tag (
                                                child.xml_name
                                                ) in self.pns_articulated
                                        )
                                ]
                        if len (names) > 1:
                                self.pns_subject = pns_name (
                                        netstring.encode (names),
                                        self.pns_horizon
                                        )
                                return self.pns_subject != ''
                                
                        if len (names) > 0:
                                self.pns_subject = names[0]
                                return True
                                
                return False
                
        def pns_articulate_cdata (self, dom):
                # articulate the element's CDATA to make a name and an
                # object:
                #
                # 1. join the CDATA with whitespace, then strip 
                # withespaces before trying to articulate a name
                self.pns_object = (
                        ' '.join (xml_utf8.xml_cdatas (self))
                        ).strip (self.sat_strip)
                # 2. extract regular expressions and simply articulate the
                # rest of the text as one public name (save the horizon
                # for latter use ...).
                if self.pns_object:
                        pns_sat_articulate (
                                self.pns_object, 
                                self.pns_horizon, 
                                self.pns_sats,
                                self.sat_re, 
                                self.sat_strip, 
                                self.sat_articulators,
                                self.sat_horizon,
                                )
                        if (
                                len (self.pns_sats) > 1 and 
                                len (self.pns_horizon) < self.sat_horizon
                                ):
                                self.pns_subject = pns_name (
                                        netstring.encode ([
                                                item[0] 
                                                for item in self.pns_sats
                                                ]),
                                        set ()
                                        )
                        elif len (self.pns_sats) > 0:
                                self.pns_subject = self.pns_sats[0][0]
                                if self.pns_subject == self.pns_object:
                                        self.pns_object = ''
                        return not (
                                self.pns_subject == '' and 
                                len (self.pns_sats) == 0
                                )
                                
                return False
        
        def pns_articulate (self, subject, context, dom):
                # SAT articulate
                if self.pns_object and self.pns_subject and len (
                        netstring.netstrings (self.pns_subject)
                        ) > 1:
                        # there is a SAT object and an articulated subject
                        if self.pns_subject == subject:
                                # make a statement in the parent's context
                                # if this element's subject is the same as
                                # its parent
                                #
                                dom.pns_statement ((
                                        self.pns_subject, 'sat', 
                                        self.pns_object, context
                                        ))
                        else:
                                # otherwise, make a statement in the context
                                # of the parent's subject
                                #
                                dom.pns_statement ((
                                        self.pns_subject, 'sat', 
                                        self.pns_object, subject
                                        ))
                elif len (self.pns_sats) > 0:
                        # there is not one SAT object or no articulated
                        # subject but there are multiple SAT statements 
                        #
                        for name, text in self.pns_sats:
                                if text and name != subject and len (
                                        netstring.netstrings (name)
                                        ) > 1:
                                        dom.pns_statement ((
                                                name, 'sat', text, subject
                                                )) 
                # XML articulate
                try:
                        tag = self.xml_name.split (' ')[1]
                except:
                        tag = self.xml_name
                        #
                        # (f*** the f***ing f***ers, let's tag ;-)
                if self.xml_string:
                        dom.pns_statement ((
                                subject, tag, self.xml_string, context
                                ))


class XML_PNS_context (XML_PNS_articulate):
        
        def xml_valid (self, dom):
                parent = self.xml_parent ()
                if parent.pns_subject == '':
                        parent.pns_articulate_children (dom)
                XML_PNS_articulate.xml_valid (self, dom)
                self.pns_articulate (
                        self.pns_subject, parent.pns_subject, dom
                        )
                xml_delete (self)
        
        def pns_articulate (self, subject, context, dom):
                # XML, no SAT for a context!
                try:
                        tag = self.xml_name.split (' ')[1]
                except:
                        tag = self.xml_name
                dom.pns_statement ((
                        subject, tag, self.xml_string, context
                        ))
                # 
                # an XML context is simply something that articulates
                # its children, then dump a "porte-manteaux" of its
                # structure to PNS in the subject of its context.


class XML_PNS_validate (XML_PNS_articulate):

        # first validate XML encoded in CDATA, then articulate
        
        def xml_valid (self, dom):
                # validate the CDATA as an XML string, use the default
                # XML_element class only and do not even try to articulate
                # unknown "foreign" markup (derived class may cleanse or 
                # recode the original CDATA first, for instance HTML using
                # Tidy and some UNICODE magic ... but that's another story).
                #
                valid = XML_dom ()
                valid.xml_unicoding = 0
                valid.xml_parser_reset ()
                e = valid.xml_parse_string (self.xml_first)
                if not e:
                        self.xml_first = self.xml_children = None
                        return
                        
                # drop any markup, add whitespaces between CDATAs
                self.pns_object = (
                        ' '.join (xml_utf8.xml_cdatas (e))
                        ).strip (self.sat_strip)
                if not self.pns_object:
                        self.xml_first = self.xml_children = None
                        return
                        
                # articulate cleansed CDATA
                pns_sat_articulate (
                        self.pns_object, 
                        self.pns_horizon,
                        self.pns_sats, 
                        self.sat_re, 
                        self.sat_strip, 
                        self.sat_articulators,
                        self.sat_horizon,
                        )
                if (
                        len (self.pns_sats) > 1 and 
                        len (self.pns_horizon) < self.sat_horizon
                        ):
                        self.pns_subject = pns_name (
                                netstring.encode (self.pns_sats),
                                set ()
                                )
                elif len (self.pns_sats) > 0:
                        self.pns_subject = self.pns_sats[0][0]
                        if self.pns_subject == self.pns_object:
                                self.pns_object = ''
                # get a valid XML string, prefixed and with namespace
                # declarations but without processing intstructions.
                # this *is* <?xml version="1.0" encoding="UTF-8"?>
                #
                self.xml_string = xml_utf8.xml_string (
                        e, valid.xml_prefixes, ''
                        )
                self.xml_first = self.xml_children = None
                #
                # Note that it writes back *valid* XML, complete with
                # namespace declaration. this will quickly overflow the
                # PNS/UDP datagram limit (1024 8-bit bytes), but that's a 
                # feature not a bug. PNS is made to articulate microformat,
                # it is not and XML database ... yet.
                #
                # A true Metabase should use 4KBytes PNS/UDP datagrams.
                #
                # That's more than enough room to store a quite large and
                # undispersed XML "porte-manteaux".
                
                                                          
class XML_PNS_delete (XML_element):
        
        # drop the element from the articulated XML tree 
        
        def xml_valid (self, dom):
                xml_delete (self)


class XML_PNS_orphan (XML_element):
        
        # remove the element from the tree and move its orphans to its
        # parent children, effectively making the element shallow to
        # the articulator

        def xml_valid (self, dom):
                xml_orphan (self)


# PNS to XML model
#
# A few functions to markup Public Names, Public RDF and PNS statements
# with XML. This is the "bread-and-butter" for XML articulation of PNS
# statements for Allegra web articulators.
#
# There are actually two sets of functions, one set for a UTF-8 only and 
# or set for UNICODE and all its encoding (the default beeing ASCII).
#
# The two sets of functions allow to either "pass-through" valid XML islands
# found in the statement object, valid CDATA strings or provide your own
# representation of this object, possibly just a <[CDATA[...]]> node but
# also an semantic graph represented by a simple XML tree.
#
# Note that the accessor must make sure to declare the PNS namespace with
# the prefix "pns":
#
#        xmlns:pns="http://pns/"
#
# in the document.


def pns_names_utf8 (name, tag='public', attr=''):
        # how elegant are Public Names in XML?
        names = netstring.netstrings (name)
        if len (names) > 1:
                return '<%s%s names="%s">%s</%s>' % (
                        tag, attr, xml_utf8.xml_attr (name),
                        ''.join ([
                                pns_names_utf8 (n, tag, attr) for n in names
                                ]), tag
                        )

        return '<%s%s name="%s" />' % (tag, attr, xml_utf8.xml_attr (name))
        #
        # Very elegant indeed
        

# TODO: rename to pns_object_utf8

def pns_cdata_utf8 (pnsobj, prefixes=None):
        if pnsobj.startswith ('<'):
                # validate what appears to be an XML string, using the
                # prefixes provided by the accessor to produce a valid
                # XML string with prefixed element tags, or escape the
                # original object if it is *not* an XML string.
                #
                return ''.join (
                        xml_utf8.xml_valid (pnsobj, prefixes)
                        ) or xml_utf8.xml_cdata (pnsobj)

        return xml_utf8.xml_cdata (pnsobj)


# TODO: rename to pns_model_utf8

def pns_xml_utf8 (model, pnsobj):
        if len (model) == 5:
                return (
                        '<pns:statement'
                        ' subject="%s" predicate="%s" context="%s"'
                        ' direction="%s" >%s</pns:pns>' % (
                                xml_utf8.xml_attr (model[0]),
                                xml_utf8.xml_attr (model[1]),
                                xml_utf8.xml_attr (model[3]),
                                model[4], # do not escape the direction!
                                pnsobj
                                )
                        )
                        
        elif len (model) == 4:
                return (
                        '<pns:statement'
                        ' subject="%s" predicate="%s" context="%s"'
                        ' >%s</pns:pns>' % (
                                xml_utf8.xml_attr (model[0]),
                                xml_utf8.xml_attr (model[1]),
                                xml_utf8.xml_attr (model[3]),
                                pnsobj
                                )
                        )

        elif len (model) == 3:
                return (
                        '<pns:statement'
                        ' subject="%s" predicate="%s"'
                        ' >%s</pns:pns>' % (
                                xml_utf8.xml_attr (model[0]),
                                xml_utf8.xml_attr (model[1]),
                                pnsobj
                                )
                        )

        return ''
        #
        # Note that this is pure markup. The original input text is available
        # as attributes, CDATA or an XML string, nothing has been lost. Yet
        # the default appearance of a PNS statement is only its objet. And,
        # last but not least, this is a concise markup, it adds the shortest
        # practical XML enveloppe possible, down to a minimum of 63 bytes if
        # there are no characters to xml_escape (or less than 7% of the
        # largest statement possible with 1024 bytes long PNS/UDP datagrams).
        
        
def pns_names_unicode (
        name, encoding='ASCII', tag='pns:public', 
        attr=' xmlns:pns="http://pns/"'
        ):
        names = netstring.netstrings (name)
        if len (names) > 1:
                return '<%s%s names="%s">%s</%s>' % (
                        tag, attr, xml_unicode.xml_attr (
                                unicode (name, 'UTF-8'), encoding
                                ), 
                        ''.join ([
                                pns_names_unicode (n, encoding, tag, attr) 
                                for n in names
                                ]), tag
                        )

        return '<%s%s name="%s" />' % (
                tag, attr, xml_unicode.xml_attr (
                        unicode (name, 'UTF-8'), encoding
                        )
                )


def pns_routes_unicode (
        routes, encoding='ASCII', tag='routes', attr=' xmlns="http://pns/"'
        ):
        if len (routes) == 0:
                return '<routes />'
                
        return '<%s%s>%s</%s>' % (
                tag, attr, ''.join ([
                        pns_names_unicode (
                                route[1], tag='route',
                                attr=' context="%s"' % xml_unicode.xml_attr (
                                        unicode (route[0], 'UTF-8')
                                        )
                                )
                        for route in routes
                        ]), tag
                )

# TODO: rename to pns_object_unicode

def pns_cdata_unicode (pnsobj, prefixes=None, encoding='ASCII'):
        if pnsobj.startswith ('<'):
                return ''.join (xml_unicode.xml_valid (
                        pnsobj, prefixes, encoding
                        )) or xml_unicode.xml_cdata (
                                unicode (pnsobj, 'UTF-8'), encoding
                                )
                                
        return xml_unicode.xml_cdata (
                unicode (pnsobj, 'UTF-8'), encoding
                )


# TODO: rename to pns_model_unicode, then split in quatuor and 
#       quintet as they *are* quite different things and drop
#       triples alltogether. 

def pns_xml_unicode (model, pnsobj, encoding='ASCII'):
        # It *is* a requirement to be able to produce something else than 
        # UTF-8. Namely ASCII. Because this is the only encoding that can be
        # expected to be supported everywhere, including by some 7bit code in
        # the chain of software consuming the XML string.
        #
        if len (model) == 5:
                return (
                        '<pns:statement'
                        ' subject="%s" predicate="%s" context="%s"'
                        ' direction="%s"'
                        ' >%s</pns:statement>' % (
                                xml_unicode.xml_attr (
                                        unicode (model[0], 'UTF-8'), encoding
                                        ),
                                xml_unicode.xml_attr (
                                        unicode (model[1], 'UTF-8'), encoding
                                        ),
                                xml_unicode.xml_attr (
                                        unicode (model[3], 'UTF-8'), encoding
                                        ),
                                model[4],
                                pnsobj
                                )
                        )
                        
        elif len (model) == 4:
                return (
                        '<pns:statement'
                        ' subject="%s" predicate="%s" context="%s"'
                        ' >%s</pns:statement>' % (
                                xml_unicode.xml_attr (
                                        unicode (model[0], 'UTF-8'), encoding
                                        ),
                                xml_unicode.xml_attr (
                                        unicode (model[1], 'UTF-8'), encoding
                                        ),
                                xml_unicode.xml_attr (
                                        unicode (model[3], 'UTF-8'), encoding
                                        ),
                                pnsobj
                                )
                        )

        elif len (model) == 3:
                return (
                        '<pns:statement'
                        ' subject="%s" predicate="%s" context=""'
                        ' >%s</pns:statement>' % (
                                xml_unicode.xml_attr (
                                        unicode (model[2], 'UTF-8'), encoding
                                        ),
                                xml_unicode.xml_attr (
                                        unicode (model[1], 'UTF-8'), encoding
                                        ),
                                pnsobj
                                )
                        )

        return ''
        #
        # exactly the same algorithm, but encoding UTF-8 to UNICODE and then
        # whatever encoding passed (ASCII by default if none specified).


if __name__ == '__main__':
        import sys, time, os
        sys.stderr.write (
                'Allegra PNS/XML'
                ' - Copyright 2005 Laurent A.V. Szyster'
                ' | Copyleft GPL 2.0\n'
                )
        if '-i' in sys.argv:
                # transform a PNS/TCP session read from stdin to an XML
                # string written to stdout. Note that only two namespaces
                # are supported by pns_xml.py: PNS's own and W3C's XHTML.
                #
                sys.argv.remove ('-i')
                t = time.time ()
                pipe = netstring.netpipe (lambda: sys.stdin.read (4096))
                encoding = 'ASCII'
                stylesheet = ''
                if len (sys.argv) > 1:
                        stylesheet = sys.argv[1]
                        if len (sys.argv) > 2:
                                encoding = sys.argv[2]
                if encoding == 'UTF-8':
                        prefixes = {
                                 'http://www.w3.org/1999/xhtml': None,
                                 'http://pns/': 'pns',
                                 'http://allegra/': 'allegra',
                                 }
                        if stylesheet:
                                stylesheet = (
                                        '<?xml-stylesheet type="text/xsl"'
                                        ' href="%s"?>' % xml_utf8.xml_attr (
                                                stylesheet
                                                )
                                        )
                        sys.stdout.write (
                                '<?xml version="1.0" encoding="UTF-8"?>'
                                '%s<allegra:pns-xml%s>' % (
                                        stylesheet,
                                        xml_utf8.xml_ns (prefixes)
                                        )
                                )
                        for encoded in pipe:
                                model = netstring.netstrings (encoded)
                                sys.stdout.write (pns_xml_utf8 (
                                        model, pns_cdata_utf8 (
                                                model[2], prefixes
                                                )
                                        ))
                else:
                        prefixes = {
                                 u'http://www.w3.org/1999/xhtml': None,
                                 u'http://pns/': u'pns',
                                 u'http://allegra/': 'allegra',
                                 }
                        if stylesheet:
                                stylesheet = (
                                        '<?xml-stylesheet type="text/xsl"'
                                        ' href="%s"'
                                        ' ?>' % xml_unicode.xml_attr (
                                                unicode (stylesheet), encoding
                                                )
                                        )
                        sys.stdout.write (
                                '<?xml version="1.0" encoding="%s"?>'
                                '%s<allegra:pns-xml%s>' % (
                                        encoding, stylesheet,
                                        xml_unicode.xml_ns (prefixes, encoding)
                                        )
                                )
                        for encoded in pipe:
                                model = netstring.netstrings (encoded)
                                sys.stdout.write (pns_xml_unicode (
                                        model, pns_cdata_unicode (
                                                model[2], prefixes, encoding
                                                ), encoding
                                        ))
                sys.stdout.write ('</allegra:pns-xml>')
                #
                # this is the minima that Allegra's PNS web interfaces
                # produce, a flat document with an XSLT processing
                # instruction that will do all of the actual presentation
                # for the user, according to his preferences. defaults
                # to a text/xsl file named "./pns.xsl" and ASCII encoding.
        else:
                # transform an XML string read from stdin into an PNS/TCP
                # session written to stdout
                #
                def pns_stdio_statement (statement):
                        encoded = netstring.encode (statement)
                        if len (encoded) > 1024:
                                sys.stderr.write (
                                        '%d:%s,' % (len (encoded), encoded)
                                        )
                                return False
                                
                        try:
                                sys.stdout.write (
                                        '%d:%s,' % (len (encoded), encoded)
                                        )
                        except Exception, error:
                                sys.stderr.write ('Exception: %r\n' % error)
                                return False
                        else:
                                return True
                
                about = sys.argv[1]
                t = time.time ()
                dom = XML_dom ()
                dom.xml_unicoding = 0
                dom.xml_class = XML_PNS_articulate
                dom.xml_classes = {}
                dom.xml_parser_reset ()
                dom.pns_subject = about
                dom.pns_statement = pns_stdio_statement
                dom.PNS_HORIZON = 126
                devnull, stdin, stderr = os.popen3 (
                        'curl %s -q' % about
                        )
                dom.xml_parse_file (stdin)
        #
        t = time.time () - t
        sys.stderr.write ('Transformed in %f secs\n' % t) 
        sys.exit ()
