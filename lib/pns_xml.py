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

from allegra import netstring, loginfo, xml_dom, pns_model, pns_sat


# XML to PNS/SAT articulation (UTF-8 encoding only!)

def xml_utf8_to_pns (e):
        "XML/PNS - serialize an UTF-8 XML element as 8-bit byte strings"
        if e.xml_attributes:
                yield netstring.encode ((
                        netstring.encode (item) 
                        for item in e.xml_attributes
                        if item[0] != 'pns' # do not pass-through the names!
                        ))
        
        else:
                yield ''
                        
        yield e.xml_first

        if e.xml_children:
                yield netstring.encode ((
                        netstring.encode ((
                                child.xml_name, child.pns_name or ''
                                ))
                        for child in e.xml_children
                        ))
        
        else:
                yield ''
                        
        yield e.xml_follow or ''

        # <p>My <a href="/blog">Blog</a> ...</p>
        #
        # yields
        #
        # 4:Blog,2:My,
        # p
        # ('', 'My', '11:1:a,4:Blog,,', '')
        # http://home/index.html
        #
        # Blog
        # a
        # ('15:4:href,5:/blog,,', 'Blog', '', ' ...')
        # 4:Blog,2:My,
        #
        # XML is marshalled into an element tree a la qp_xml.py,
        # encoded as UTF-8, a fast format to instanciate as a
        # DOM and/or serialize back to XML.
        #
        # With 1024 bytes PNS/UDP datagram it is enough to
        # marshall RSS and many concise XML protocols, but for
        # XHTML or DocBook, 4KB or bigger datagrams are probably
        # required (unless of course you just want to index it all,
        # not store it all ;-)

def xml_utf8_chunk (element, dom):
        if element.xml_children:
                element.pns_sat_articulated = []
                pns_sat.articulate_chunk (
                        ' '.join (xml_utf8.xml_cdatas (element)),
                        element.pns_sat_articulated.append,
                        element.pns_sat_language or dom.pns_sat_language,
                        element.PNS_SAT_CHUNK
                        )
        elif element.xml_first:
                element.pns_sat_articulated = []
                pns_sat.articulate_chunk (
                        element.xml_first, 
                        element.pns_sat_articulated.append,
                        element.pns_sat_language or dom.pns_sat_language,
                        element.PNS_SAT_CHUNK
                        )
        else:
                return


def xml_utf8_name (element, dom):
        if element.xml_children:
                element.pns_sat_articulated = []
                element.pns_name = pns_sat.articulate_re (
                        ' '.join (xml_utf8.xml_cdatas (element)),
                        element.pns_sat_articulated.append,
                        element.pns_sat_language or dom.pns_sat_language
                        )
        elif element.xml_first:
                element.pns_sat_articulated = []
                element.pns_name = pns_sat.articulate_re (
                        element.xml_first, 
                        element.pns_sat_articulated.append,
                        element.pns_sat_language or dom.pns_sat_language
                        )
        else:
                return
        

def xml_utf8_context (element, dom):
        # articulate a context from the child's name(s)
        #
        field = set ()
        element.pns_name = pns_model.pns_name (netstring.encode ((
                child.pns_name for child in element.xml_children 
                if child.pns_name
                )), field)
        for child in element.xml_children:
                if child.pns_name:
                        dom.pns_statement ((
                                child.pns_name,
                                child.xml_name,
                                netstring.encode (xml_utf8_to_pns (child)),
                                element.pns_name
                                ))
                else:
                        dom.pns_statement ((
                                element.pns_name,
                                child.xml_name,
                                netstring.encode (xml_utf8_to_pns (child)),
                                dom.pns_name
                                ))
                # articulate the child SATs in this element's context
                for articulated in child.pns_sat_articulated:
                        if not dom.pns_statement ((
                                articulated[2], 
                                'sat', 
                                articulated[3],
                                element.pns_name
                                )):
                                break
                                #
                                # stop if a statement is too long, articulated
                                # names are sorted by length, bigger last!


class Articulate (xml_dom.XML_element):
                
        pns_name = None
        pns_sat_language = None
        pns_sat_articulated = ()
        PNS_SAT_CHUNK = 504
        
        def xml_valid (self, dom):
                if self.xml_children:
                        if self.xml_attributes.has_key ('pns'):
                                xml_utf8_context (self, dom)
                        else:
                                xml_dom.xml_sparse (self, dom)
                if (
                        self.xml_attributes and 
                        self.xml_attributes.has_key ('pns')
                        ):
                        xml_utf8_name (self, dom)
                else:
                        xml_utf8_chunk (self, dom)


# PNS/UDP Constant

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


def articulate (
        dom, name, lang, types, 
        type=Articulate, statement=log_statement
        ):
        dom.pns_name = name
        dom.pns_sat_language = pns_sat.language (lang)
        dom.xml_types = types
        dom.xml_type = type
        dom.xml_unicoding = 0
        dom.pns_statement = statement
        return dom
        #
        # XML/PNS articulators are "sparse" XML tree parsers, named and 
        # articulated in a default language, for a set of element types.
        #
        # Synopsis:
        #
        # xml_utf8_articulate (
        #    xml_reactor.XML_collector (), 
        #    'http://...', 'en', pns_rss.RSS_20, log_statement
        #    )


# PNS/XML proper, store and retrieve XML documents from a PNS metabase

def xml_unicode_to_pns (e):
        "XML/PNS - serialize a UNICODEd XML element as 8-bit byte strings"
        if e.xml_attributes:
                yield netstring.encode ((
                        netstring.encode ((
                                key.encode ('utf-8'), val.encode ('utf-8')
                                ))
                        for key, val in e.xml_attributes
                        if key != u'pns'
                        ))
        
        else:
                yield ''
                        
        yield e.xml_first.encode ('utf-8')

        if e.xml_children:
                yield netstring.encode ((
                        netstring.encode ((
                                child.xml_name.encode ('utf-8'), 
                                child.pns_name
                                ))
                        for child in e.xml_children
                        ))
        
        else:
                yield ''
                        
        yield e.xml_follow.encode ('utf-8') or ''


def xml_to_pns (element, context):
        subject = element.xml_attributes.get (u'pns', u'').encode (
                'utf-8'
                ) or context
        if dom.pns_statement ((
                subject, 
                element.xml_name,
                netstring.encode (xml_unicode_to_pns (element)),
                context
                )):
                for child in element.xml_children:
                        if not xml_to_pns (child, context):
                                child.pns_name = None
                return True

        return False

def pns_to_xml_unicode (e, encoded):
        "PNS/XML - flesh out an XML element with UNICODE strings"
        attributes, first, children, follow = netstring.decode (encoded)
        if attributes:
                e.xml_attributes = dict ((
                        (
                                unicode (s, 'utf-8') 
                                for s in netstring.decode (pair)
                                )
                        for item in netstring.decode (attributes)
                        ))
                if e.pns_name:
                        e.xml_attributes[u'pns'] = unicode (
                                e.pns_name, 'utf-8'
                                )
        elif e.pns_name:
                e.xml_attributes = {u'pns': unicode (e.pns_name, 'utf-8')}
        if first:
                e.xml_first = unicode (first, 'utf-8')
        else:
                e.xml_first = u''
        if follow:
                e.xml_follow = unicode (follow, 'utf-8')
        if children:
                return (
                        tuple (netstring.decode (child))
                        for child in netstring.decode (children)
                        )
                # return a generator if there are children


# Note about this implementation
#
# <rss>
#   <channel>            
#     <title>...</title> # articulate and name
#     <item>               
#       <title>...</title> # articulate and names
#       <description>...</description> # articulate, maybe name
#     </item> # makes statements about its title, description
#   </channel> # make statements about its title, item(s)
# </rss>
#
#
# <html>
#   <head><title>...</title></head> # articulate and name
#   <body>
#     <h1>...</h1> # articulate and name
#     <p>...</p> # articulate, maybe name
#   </body>
# </html>