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

import weakref

from allegra import (
        netstring, loginfo, finalization, xml_dom, 
        pns_model, pns_sat, pns_client, pns_articulator
        )


# XML to PNS/SAT articulation (UTF-8 encoding only!)

def xml_utf8_articulate (e):
        "XML/PNS - articulate an UTF-8 XML element as 8-bit byte strings"
        if e.xml_attributes:
                yield netstring.encode ((
                        netstring.encode (item) 
                        for item in e.xml_attributes.items ()
                        ))
        else:
                yield ''
                        
        yield e.xml_first

        if e.xml_children:
                yield netstring.encode ((
                        netstring.encode ((
                                child.xml_name, child.pns_name
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
        if not element.xml_children:
                return
        
        # articulate a context from the child's name(s)
        #
        field = set ()
        name = element.pns_name = pns_model.pns_name (netstring.encode ((
                child.pns_name for child in element.xml_children 
                if child.pns_name
                )), field)
        if not name:
                return

        for child in element.xml_children:
                # articulate XML
                if child.pns_name:
                        dom.pns_statement ((
                                child.pns_name,
                                child.xml_name,
                                netstring.encode (
                                        xml_utf8_articulate (child)
                                        ),
                                dom.pns_name
                                ))
                else:
                        dom.pns_statement ((
                                name,
                                child.xml_name,
                                netstring.encode (
                                        xml_utf8_articulate (child)
                                        ),
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


class Inarticulate (xml_dom.XML_element):
        
        pns_name = None
        pns_sat_articulated = ()


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

def xml_utf8_pns_name (attributes):
        try:
                return attributes['pns']
        
        except:
                return ''
        

def xml_utf8_to_pns (e):
        "XML/PNS - serialize an UTF-8 XML element as 8-bit byte strings"
        if e.xml_attributes:
                yield netstring.encode ((
                        netstring.encode (item) 
                        for item in e.xml_attributes.items ()
                        ))
        else:
                yield ''
                        
        yield e.xml_first

        if e.xml_children:
                yield netstring.encode ((
                        netstring.encode ((
                                child.xml_name, child.pns_name
                                ))
                        for child in e.xml_children
                        ))
        
        else:
                yield ''
                        
        yield e.xml_follow or ''


def xml_unicode_to_pns (e):
        "XML/PNS - serialize a UNICODEd XML element as 8-bit byte strings"
        if e.xml_attributes:
                yield netstring.encode ((
                        netstring.encode ((
                                key.encode ('utf-8'), val.encode ('utf-8')
                                ))
                        for key, val in e.xml_attributes.items ()
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


def xml_to_pns (element, context, statement):
        subject = element.xml_attributes.get (u'pns', u'').encode (
                'utf-8'
                ) or context
        if statement ((
                subject, 
                element.xml_name,
                netstring.encode (xml_unicode_to_pns (element)),
                context
                )):
                for child in element.xml_children:
                        if not xml_to_pns (child, context, statement):
                                child.pns_name = None
                return True

        return False



class PNS_XML_continuation (finalization.Finalization):
        
        # this instance is finalized as soon as its pns_response bound
        # method is dereferenced by the pns_client to which it was
        # passed as handler for a statement's response(s).
        #
        # This *is* a little bit heavy and should be merged with the
        # XML element itself, but that will require some changes to
        # the xml_dom.py interfaces that I'm not yet ready to make ...
        
        xml_parsed = None
        
        def __init__ (self, dom, question):
                self.pns_question = question
                self.pns_dom = dom
        
        def __call__ (self, finalized):
                # join a child element response continuation
                assert None == loginfo.log (
                        finalized.pns_question, 'join'
                        )
                child = finalized.xml_parsed
                sibblings = self.xml_parsed.xml_children
                sibblings[sibblings.index (finalized.pns_question)] = child
                child.xml_parent = weakref.ref (self.xml_parsed)
                if child.xml_valid != None:
                        child.xml_valid (self.pns_dom)

        def pns_to_xml_utf8 (self, resolved, model):
                assert None == loginfo.log (
                        netstring.encode (model), 'resolved'
                        )
                if model[4][0] in ('.', '?'):
                        return False
                
                # try to decode the PNS/XML element 
                try:
                        attr, first, children, follow = \
                                netstring.decode (model[2])
                except:
                        return False
                        
                # decode the attributes and set the pns attribute
                if attr:
                        attr = dict ((
                                tuple (netstring.decode (item))
                                for item in netstring.decode (attr)
                                ))
                        attr['pns'] = model[0]
                else:
                        attr = {'pns': model[0]}
                # instanciate a named XML element type
                self.xml_parsed = e = self.pns_dom.xml_types.get (
                        model[1], self.pns_dom.xml_type
                        ) (model[1], attr)
                if first:
                        e.xml_first = first
                else:
                        e.xml_first = ''
                if follow:
                        e.xml_follow = follow
                # decode the children's name and subject,
                if children:
                        e.xml_children = list (netstring.decode (children))
                        for child in e.xml_children:
                                name, subject = tuple (
                                        netstring.decode (child)
                                        )
                                joined = PNS_XML_continuation (
                                        self.pns_dom, child
                                        )
                                self.pns_dom.pns_statement (
                                        (subject or model[0], name, ''), 
                                        self.pns_dom.pns_name, 
                                        joined.pns_to_xml_unicode
                                        )
                                joined.finalization = self
                return False

        def pns_to_xml_unicode (self, resolved, model):
                assert None == loginfo.log (
                        netstring.encode (model), 'resolved'
                        )
                if model[4][0] in ('.', '?'):
                        return False
                
                # try to decode the PNS/XML element 
                try:
                        attr, first, children, follow = \
                                netstring.decode (model[2])
                except:
                        return False
                        
                # decode the attributes and set the pns attribute
                if attr:
                        attr = dict ((
                                tuple ((
                                        unicode (s, 'utf-8') 
                                        for s in netstring.decode (item)
                                        ))
                                for item in netstring.decode (attr)
                                ))
                        attr[u'pns'] = unicode (model[0], 'utf-8')
                else:
                        attr = {u'pns': unicode (model[0], 'utf-8')}
                # instanciate a named XML element type
                self.xml_parsed = e = self.pns_dom.xml_types.get (
                        model[1], self.pns_dom.xml_type
                        ) (model[1], attr)
                if first:
                        e.xml_first = unicode (first, 'utf-8')
                else:
                        e.xml_first = u''
                if follow:
                        e.xml_follow = unicode (follow, 'utf-8')
                # decode the children's name and subject,
                if children:
                        e.xml_children = list (netstring.decode (children))
                        for child in e.xml_children:
                                name, subject = tuple (
                                        netstring.decode (child)
                                        )
                                joined = PNS_XML_continuation (
                                        self.pns_dom, child
                                        )
                                self.pns_dom.pns_statement (
                                        (subject or model[0], name, ''), 
                                        self.pns_dom.pns_name, 
                                        joined.pns_to_xml_unicode
                                        )
                                joined.finalization = self
                return False


class PNS_DOM (object):
        
        xml_type = xml_dom.XML_element
        xml_types = {}
        xml_unicoding = True
        xml_root = None
        
        pns_name = pns_statement = None
        
        def __init__ (self, prefixes=None, pi=None):
                self.xml_prefixes = prefixes or {}
                self.xml_pi = pi or {}
                
        def pns_to_xml (self, name, subject, context, statement):
                self.pns_name = context
                self.pns_statement = statement
                finalized = PNS_XML_continuation (self, None)
                if self.xml_unicoding:
                        statement (
                                (subject, name, ''), context,
                                finalized.pns_to_xml_unicode 
                                )
                else:
                        statement (
                                (subject, name, ''), context, 
                                finalized.pns_to_xml_utf8 
                                )
                finalized.finalization = self.pns_to_xml_continue
                        
        def pns_to_xml_continue (self, finalized):
                assert None == loginfo.log (
                        '%r' % finalized.xml_parsed, 'debug'
                        )
                e = finalized.xml_parsed
                if e and e.xml_valid != None:
                        e.xml_valid (self)
                self.xml_root = e

        def xml_to_pns (self, name, subject, context, statement):
                self.pns_name = context
                self.pns_statement = statement
                statement ((
                        subject, xml_root.xml_name, 
                        xml_unicode_to_pns (self.xml_root)
                        ), context, self.xml_unicode_to_pns)
                        
        def xml_unicode_to_pns (self, resolved, model):
                if model[4] == '_':
                        pass
                elif model[4] == '.':
                        pass
                elif model[4] == '?':
                        pass
                elif model[4] == '!':
                        pass
                else:
                        pass

        
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