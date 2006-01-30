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

from allegra import (
        netstring, loginfo,              # Asynchronous Network Peer 
        xml_dom, xml_utf8, xml_unicode,  # Internet Application Protocols
        pns_model, pns_sat               # PNS Reference Implementation
        )


# XML to PNS articulation (UTF-8 encoding only!)

# PNS/SAT Parameters

SAT_RE = {
        'en': pns_sat.SAT_ARTICULATE_EN,
        'fr': pns_sat.SAT_ARTICULATE_FR,
        }

SAT_CHUNK = 504

XML_LANG = 'en'

PNS_LENGTH = 1024


# What to do with the PNS Statement tuple produced

def log_statement (model):
        "Log valid statement to STDOUT, errors to STDERR"
        #
        # Length validation, extracted from PNS/Model (there is no need
        # to valide the subject and context as Public Names, this should
        # have been allready done!)
        #
        if model[0]:
                sp_len = len (model[0]) + len (model[1]) + len (
                        '%d%d' % (len (model[0]), len (model[1]))
                        )
                if sp_len > PNS_LENGTH/2:
                        assert None == loginfo.log (
                                netstring.encode (model), 
                                '3 invalid statement length %d' % sp_len
                                )
                        return False

                if model[2]:
                        model = (model[0], model[1], model[2][:(
                                PNS_LENGTH - sp_len - len (
                                        '%d' % (PNS_LENGTH - sp_len)
                                        )
                                )], model[3])
        loginfo.log (netstring.encode (model))
        return True


# The PNS/XML Articulators for context and subject markup, CDATA elements
# and enclosure (XHTML embedded in a description for instance, etc ...),
# attributed as methods to all or one of the three classes below.

def articulate_context (self, dom):
        parent = self.xml_parent ()
        if parent.pns_subject == '':
                articulate_children (parent, dom)
        articulate_subject (self, dom)
        self.pns_articulate (self.pns_subject, parent.pns_subject, dom)
        xml_dom.xml_delete (self)
        

def articulate_subject (self, dom):
        self.xml_first = (self.xml_first or '').strip (
                self.SAT_STRIP
                )
        if self.xml_parent:
                self.pns_context = self.xml_parent ().pns_subject
        if self.xml_children and (
                articulate_children (self, dom) or articulate_cdata (self, dom)
                ):
                # let children articulate in the context of this
                # element's subject ...
                for child in self.xml_children:
                        child.xml_follow = (
                                child.xml_follow or ''
                                ).strip (self.SAT_STRIP)
                        child.pns_articulate (
                                self.pns_subject, 
                                self.pns_context or dom.pns_subject, 
                                dom
                                )
                self.xml_string = xml_utf8.xml_string (
                        self, dom.xml_prefixes, ''
                        )
        elif articulate_cdata (self, dom):
                # self.xml_string = self.xml_first
                self.xml_string = xml_utf8.xml_string (self, None, '')
                self.xml_attributes = None
        self.xml_first = self.xml_children = None
        
        
def articulate_children (self, dom):
        if self.xml_children:
                names = [
                        child.pns_subject 
                        for child in self.xml_children
                        if (child.pns_subject and xml_utf8.xml_tag (
                                child.xml_name
                                ) in self.pns_articulated)
                        ]
                if len (names) > 1:
                        self.pns_subject = pns_model.pns_name (
                                netstring.encode (names), self.pns_horizon
                                )
                        return self.pns_subject != ''
                        
                if len (names) > 0:
                        self.pns_subject = names[0]
                        return True
                        
        return False

        
def articulate_cdata (self, dom):
        # articulate the element's CDATA to make a name and an
        # object:
        #
        # 1. join the CDATA with whitespace, then strip 
        # withespaces before trying to articulate a name
        SAT_STRIP = self.SAT_STRIP or dom.SAT_STRIP
        self.pns_object = (
                ' '.join (xml_utf8.xml_cdatas (self))
                ).strip (SAT_STRIP)
        # 2. extract regular expressions and simply articulate the
        # rest of the text as one public name (save the horizon
        # for latter use ...).
        if self.pns_object:
                SAT_RE = self.SAT_RE or dom.SAT_RE
                SAT_HORIZON = self.SAT_HORIZON or dom.SAT_HORIZON
                pns_sat.pns_sat_chunk (
                        self.pns_object, self.pns_horizon, self.pns_sats,
                        SAT_RE, SAT_CHUNK, SAT_STRIP, SAT_HORIZON, 0
                        )
                if (
                        len (self.pns_sats) > 1 and 
                        len (self.pns_horizon) < SAT_HORIZON
                        ):
                        self.pns_subject = pns_model.pns_name (
                                netstring.encode ([
                                        item[0] for item in self.pns_sats
                                        ]), set ()
                                )
                elif len (self.pns_sats) > 0:
                        self.pns_subject = self.pns_sats[0][0]
                        if self.pns_subject == self.pns_object:
                                self.pns_object = ''
                return not (
                        self.pns_subject == '' and len (self.pns_sats) == 0
                        )
                        
        return False


def articulate_enclosure (self, dom):
        # validate the CDATA as an XML string, use the default
        # XML_element class only and do not even try to articulate
        # unknown "foreign" markup (derived class may cleanse or 
        # recode the original CDATA first, for instance HTML using
        # Tidy and some UNICODE magic ... but that's another story).
        #
        valid = xml_dom.parse_string (self.xml_first, unicoding=0)
        if not valid.xml_root:
                self.xml_first = self.xml_children = None
                return
                
        # drop any markup, add whitespaces between CDATAs
        SAT_STRIP = self.SAT_STRIP or dom.SAT_STRIP
        self.pns_object = (
                ' '.join (xml_utf8.xml_cdatas (dom.xml_root))
                ).strip (SAT_STRIP)
        if not self.pns_object:
                self.xml_first = self.xml_children = None
                return
                
        # articulate cleansed CDATA
        SAT_RE = self.SAT_RE or dom.SAT_RE
        SAT_HORIZON = self.SAT_HORIZON or dom.SAT_HORIZON
        pns_sat.pns_sat_chunk (
                self.pns_object, self.pns_horizon, self.pns_sats, 
                SAT_RE, SAT_CHUNK, SAT_STRIP, SAT_HORIZON, 0
                )
        if (
                len (self.pns_sats) > 1 and 
                len (self.pns_horizon) < SAT_HORIZON
                ):
                self.pns_subject = pns_model.pns_name (
                        netstring.encode (self.pns_sats),
                        set ()
                        )
        elif len (self.pns_sats) > 0:
                self.pns_subject = self.pns_sats[0][0]
                if self.pns_subject == self.pns_object:
                        self.pns_object = ''
        #
        # get a valid XML string, prefixed and with namespace
        # declarations but without processing intstructions.
        # this *is* <?xml version="1.0" encoding="UTF-8"?>
        #
        self.xml_string = xml_utf8.xml_string (
                valid.xml_root, valid.xml_prefixes
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
        

class XML_PNS_subject (xml_dom.XML_element):
        
        # The basic RE articulator type, your mileage may vary ...
        
        pns_context = pns_subject = pns_object = xml_string = ''

        SAT_RE = SAT_RE[XML_LANG]
        SAT_STRIP = pns_sat.SAT_STRIP_UTF8
        SAT_HORIZON = 126

        pns_articulated = set ()

        def __init__ (self, name, attributes):
                self.pns_horizon = set ()
                self.pns_sats = []
                try:
                        self.SAT_RE = SAT_RE[attributes[
                                'http://www.w3.org/XML/1998/namespace lang'
                                ]]
                except KeyError:
                        parent = self.xml_parent
                        while parent:
                                try:
                                        self.SAT_RE = parent.SAT_RE
                                except:
                                        parent = parent.xml_parent
                                else:
                                        break
                                
                xml_dom.XML_element.__init__ (self, name, attributes)
                
        xml_valid = articulate_subject

        def pns_articulate (self, subject, context, dom):
                # SAT articulate
                if self.pns_object and self.pns_subject and len (
                        netstring.netlist (self.pns_subject)
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
                                        netstring.netlist (name)
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
        

class XML_PNS_context (XML_PNS_subject):
        
        xml_valid = articulate_context
        
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


class XML_PNS_enclosure (XML_PNS_subject):

        # first validate XML encoded in CDATA, then articulate
        
        xml_valid = articulate_enclosure
                
                                                          
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
        names = netstring.netlist (name)
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
        names = netstring.netlist (name)
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
                                model = netstring.netlist (encoded)
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
                                model = netstring.netlist (encoded)
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
                dom = xml_dom.XML_dom ()
                dom.xml_unicoding = 0
                dom.xml_type = XML_PNS_articulate
                dom.xml_types = {}
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


# PNS/XML Synopsis:
#
# GET http://home.com/mypage.html HTTP/1.1
# <html>
# <head><title>My Home Page</title>
# <body>This is my home page on the 
# <a href="www.w3.org">World Wide Web</a>.</body>
# </html>
#
# 4:Home,2:My,4:Page,
# title
# <title>My Home Page</title>
# http://home.com/mypage.html
#
# 4:This,...
# body
# <body>This is my home page on the <a name="3:Web,4:Wide,6:World,"/>.</body>
# http://home.com/mypage.html
#
# 3:Web,4:Wide,6:World,
# a
# <a href="www.w3.org">World Wide Web</a>.
# 4:This,...
#
# http://home.com/mypage.html
# html
# <head><title name="4:Home,2:My,4:Page,"/></head><body name="4:This,..."/>
# 19:4:Home,2:My,4:Page,,?4:This,...
#
# 
# An PNS/XML Metabase
#
# This module is designed to transform an XML string into a string of
# Public RDF statements. It will "granularize" any large and complex
# document into a sequence of well-articulated statements made to a
# PNS metabase. And it does it as to allow a PNS user agent to aggregate
# the documents or parts of it by "pulling" the document as far as required
# for its application.
#
# What a PNS/XML metabase contains is a large set of atomic statements
# with an UTF-8 encoded XML string as object (and possibly an invalid
# one, trunkated to the limit of the PNS/UDP datagram size).
#
# The challenge for a PNS/XML user agent is to slice input in such way
# as to produce statements that fill most of the PNS/UDP datagram but
# not all. For instance, most of the essential markup and CDATA of an
# RSS item may fit a 1024 bytes datagram, but certainly not a fat one
# with all its description, content and application links.
#
# The X classes provided to develop simple PNS/XML articulators fit
# common cases: 
#
# 1. no children and large text, an RSS description.
# 2. no children and small text, RSS title and HTML anchors.
# 3. children, RSS item or HTML paragraph.
#
#
# Caveat!
#
# Any PNS/XML application should validate an XML string and must validate
# the one that fills the PNS/UDP datagram. Under the assumption of a strictly
# private metabase fed with valid XML strings only, a PNS/XML metabase
# application may simply dump the XML retrieved.
#
# Note also that the PNS/XML transformer expect expat to return UTF-8 encoded
# 8-bit byte strings, not UNICODE.