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
        netstring, loginfo, finalization, 
        xml_dom, xml_utf8, xml_unicode, 
        pns_model, pns_sat, pns_client
        )


# PNS/XML definition

def xml_utf8_to_pns (e):
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
                                child.pns_name, child.xml_name
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

def xml_unicode_to_pns (e):
        "XML/PNS - serialize a UNICODEd XML element as 8-bit byte strings"
        if e.xml_attributes:
                yield netstring.encode ((
                        netstring.encode ((
                                key.encode ('utf-8'), val.encode ('utf-8')
                                ))
                        for key, val in e.xml_attributes.items ()
                        ))
        
        else:
                yield ''
                        
        yield e.xml_first.encode ('utf-8')

        if e.xml_children:
                yield netstring.encode ((
                        netstring.encode ((
                                child.pns_name, 
                                child.xml_name.encode ('utf-8')
                                ))
                        for child in e.xml_children
                        ))
        
        else:
                yield ''
                   
        if e.xml_follow:
                yield e.xml_follow.encode ('utf-8')
        
        else:
                yield ''


# XML to PNS/SAT articulation (UTF-8 encoding only!)

def xml_utf8_sat (element, dom):
        if element.xml_children:
                element.pns_sat_articulated = []
                return pns_sat.articulate_re (
                        ' '.join (xml_utf8.xml_cdatas (element)),
                        element.pns_sat_articulated.append,
                        element.pns_sat_language or dom.pns_sat_language
                        )
                        
        elif element.xml_first:
                element.pns_sat_articulated = []
                return pns_sat.articulate_re (
                        element.xml_first, 
                        element.pns_sat_articulated.append,
                        element.pns_sat_language or dom.pns_sat_language
                        )
                        
        
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


def xml_utf8_name (element, dom):
        # articulate a context's name one from its children's name(s)
        field = set ()
        return pns_model.pns_name (netstring.encode ((
                child.pns_name 
                for child in element.xml_children 
                if child.pns_name
                )), field)
                

def xml_utf8_context (element, dom):
        if not element.xml_children:
                return
        
        context = element.pns_name or dom.pns_name
        for child in element.xml_children:
                # A PNS/XML statement with the same context and subject is a
                # leaf. All other are branches, that have their parent's name
                # has contexts but not as subject.
                #
                dom.pns_statement ((
                        child.pns_name or context,
                        child.xml_name,
                        netstring.encode (xml_utf8_to_pns (child)),
                        context
                        ))
                child.xml_children = None # drop articulated children now!
                # articulate the child SATs in this element's context
                for articulated in child.pns_sat_articulated:
                        if not dom.pns_statement ((
                                articulated[2], 'sat', articulated[3], context
                                )):
                                break
                                #
                                # stop if a statement is too long, articulated
                                # names are sorted by length, bigger last!


def xml_utf8_root (element, dom):
        xml_utf8_context (element, dom)
        dom.pns_statement ((
                element.pns_name or dom.pns_name,
                element.xml_name,
                netstring.encode (
                        xml_utf8_to_pns (element)
                        ),
                dom.pns_name
                ))


class Articulate (xml_dom.Element):
                
        pns_name = ''
        pns_sat_language = None
        pns_sat_articulated = ()
        PNS_SAT_CHUNK = 504
        
        def xml_valid (self, dom):
                # articulate a named context, a nameless context, name a
                # context and articulate SAT or just articulate SAT, maybe
                # chunk it if the first CDATA is too big.
                #
                if self.xml_children:
                        if (
                                self.xml_attributes and 
                                self.xml_attributes.has_key ('pns')
                                ):
                                self.pns_name = xml_utf8_name (self, dom)
                        xml_utf8_context (self, dom)
                if (
                        self.xml_attributes and 
                        self.xml_attributes.has_key ('pns')
                        ):
                        self.pns_name = xml_utf8_sat (self, dom)
                elif len (self.xml_first) < self.PNS_SAT_CHUNK:
                        xml_utf8_sat (self, dom)
                else:
                        xml_utf8_chunk (self, dom)
                

class Inarticulate (xml_dom.Element):
        
        pns_name = ''
        pns_sat_articulated = ()


# PNS/UDP Constant

PNS_LENGTH = 1024


# What to do with the PNS Statement tuple produced

def log_statement (model):
        "Log valid statement to STDOUT, errors to STDERR"
        model, error = pns_model.pns_triple (model)
        if error:
                loginfo.log (netstring.encode (model), error)
                return False
        
        loginfo.log (netstring.encode (model))
        return True


def articulate (
        dom, name, types, 
        type=Articulate, statement=log_statement
        ):
        dom.pns_name = name
        dom.xml_types = types
        dom.xml_type = type
        dom.xml_unicoding = 0
        dom.pns_statement = statement
        dom.pns_sat_language = pns_sat.language ()
        return dom
        #
        # XML/PNS articulators are "sparse" XML tree parsers, named and 
        # articulated in a default language, for a set of element types.
        #
        # Synopsis:
        #
        # from allegra impor xml_reactor, pns_xml
        # pns_xml.articulate (
        #    xml_reactor.XML_collector (), 
        #    'http://...', pns_rss.RSS_20, log_statement
        #    )


# PNS/XML proper, store and retrieve XML documents from a PNS metabase

def pns_to_xml_utf8 (model, xml_types={}, xml_type=xml_dom.Element):
        # try to decode the PNS/XML element 
        try:
                attr, first, children, follow = netstring.validate (
                        model[2], 4
                        )
        except:
                if model[0] != model[3]:
                        attr = {'pns': model[0]}
                else:
                        attr = None
                e = xml_types.get (model[1], xml_type) (
                        model[1] or 'http://allegra/ pns-xml-error', attr
                        )
                e.xml_first = model[2]
                return e, None
                
        # decode the attributes and set the pns attribute
        if attr:
                attr = dict ((
                        tuple (netstring.decode (item))
                        for item in netstring.decode (attr)
                        ))
                if model[0] != model[3]:
                        attr['pns'] = model[0]
        elif model[0] != model[3]:
                attr = {'pns': model[0]}
        else:
                attr = None
        e = xml_types.get (model[1], xml_type) (model[1], attr)
        if first:
                e.xml_first = first
        else:
                e.xml_first = ''
        if follow:
                e.xml_follow = follow
        return e, children


def pns_to_xml_unicode (model, xml_types={}, xml_type=xml_dom.Element):
        name = unicode (model[1], 'utf-8')
        # try to decode the PNS/XML element 
        try:
                attr, first, children, follow = netstring.validate (
                        model[2], 4
                        )
        except:
                # if no PNS/XML element is encoded in the statement object,
                # consider the predicate as the element name, the object as 
                # first CDATA and the subject as only attribute if it is
                # distinct from the statement's context. in effect, translate
                # *any* PNS statement to an XML element:
                #
                # <predicate pns="subject">object</predicate>
                #
                if model[0] != model[3]:
                        attr = {u'pns': unicode (model[0], 'utf-8')}
                else:
                        attr = None
                e = xml_types.get (name, xml_type) (
                        name or u'http://allegra/ pns-xml-error', attr
                        )
                if model[2]:
                        e.xml_first = unicode (model[2], 'utf-8')
                else:
                        e.xml_first = u''
                return e, None
                
        # decode the attributes and set the pns attribute
        if attr:
                attr = dict ((
                        tuple ((
                                unicode (s, 'utf-8')
                                for s in netstring.decode (item)
                                ))
                        for item in netstring.decode (attr)
                        ))
                if model[0] != model[3]:
                        attr[u'pns'] = unicode (model[0], 'utf-8')
        elif model[0] != model[3]:
                attr = {u'pns': unicode (model[0], 'utf-8')}
        else:
                attr = None
        # decode the name and instanciate an XML element
        e = xml_types.get (name, xml_type) (name, attr)
        if first:
                e.xml_first = unicode (first, 'utf-8')
        else:
                e.xml_first = u''
        if follow:
                e.xml_follow = unicode (follow, 'utf-8')
        return e, children


class PNS_XML_continuation (finalization.Finalization):
        
        # this instance is finalized as soon as its pns_response bound
        # method is dereferenced by the pns_client to which it was
        # passed as handler for a statement's response(s).
        #
        # This *is* a little bit heavy and should be merged with the
        # XML element itself, but that will require some changes to
        # the xml_dom.py interfaces that I'm not yet ready to make ...
        
        xml_children = xml_parsed = None
        
        def __init__ (self, dom, question):
                self.pns_question = question
                self.pns_dom = dom
        
        def __call__ (self, finalized):
                # join a child element response continuation
                child = finalized.xml_parsed
                sibblings = self.xml_parsed.xml_children
                if child == None:
                        sibblings.remove (finalized.pns_question)
                        return

                sibblings[sibblings.index (finalized.pns_question)] = child
                child.xml_parent = weakref.ref (self.xml_parsed)
                if child.xml_valid != None:
                        child.xml_valid (self.pns_dom)

        def pns_to_xml_utf8 (self, resolved, model):
                if model[4][0] in ('.', '?'):
                        return False
                
                self.xml_parsed, children = pns_to_xml_utf8 (
                        model, self.pns_dom.xml_types, self.pns_dom.xml_type
                        )
                # decode the children's name and subject,
                if children:
                        self.xml_parsed.xml_children = children = list (
                                netstring.decode (children)
                                )
                        for child in children:
                                subject, name = tuple (
                                        netstring.decode (child)
                                        )
                                if subject:
                                        context = model[0]
                                else:
                                        context = subject = model[0]
                                joined = PNS_XML_continuation (
                                        self.pns_dom, child
                                        )
                                self.pns_dom.pns_statement (
                                        (subject, name, ''), context,
                                        joined.pns_to_xml_unicode
                                        )
                                joined.finalization = self
                return False

        def pns_to_xml_unicode (self, resolved, model):
                if model[4][0] in ('.', '?'):
                        return False
                
                self.xml_parsed, children = pns_to_xml_unicode (
                        model, self.pns_dom.xml_types, self.pns_dom.xml_type
                        )
                if children:
                        self.xml_parsed.xml_children = children = list (
                                netstring.decode (children)
                                )
                        for child in children:
                                subject, name = tuple (
                                        netstring.decode (child)
                                        )
                                if subject:
                                        context = model[0]
                                else:
                                        context = subject = model[0]
                                joined = PNS_XML_continuation (
                                        self.pns_dom, child
                                        )
                                self.pns_dom.pns_statement (
                                        (subject, name, ''), context,
                                        joined.pns_to_xml_unicode
                                        )
                                joined.finalization = self
                return False


class PNS_XML_continuations (PNS_XML_continuation):
        
        pns_contexts = None
        
        def __call__ (self, finalized):
                # join a child element response continuation
                child = finalized.xml_parsed
                parent = self.pns_contexts[finalized.pns_context]
                sibblings = parent.xml_children
                if child == None:
                        sibblings.remove (finalized.pns_question)
                        return

                sibblings[sibblings.index (finalized.pns_question)] = child
                child.xml_parent = weakref.ref (parent)
                if child.xml_valid != None:
                        child.xml_valid (self.pns_dom)

        def pns_to_xml_utf8_a (self, resolved, model):
                if model[4] != ('_') or model[2] == '':
                        return False
                
                self.pns_contexts = {}
                question = resolved[:2]
                for co in netstring.decode (model[2]):
                        c, o = netstring.decode (co) # TODO? fix this
                        self.pns_to_xml_utf8 (
                                resolved, question+(o, c, '_')
                                )
                        self.pns_contexts[c] = self.xml_parsed
                self.xml_parsed = None
                return False

        def pns_to_xml_unicode (self, resolved, model):
                self.xml_parsed, children = pns_to_xml_unicode (
                        model, self.pns_dom.xml_types, self.pns_dom.xml_type
                        )
                if children:
                        self.xml_parsed.xml_children = children = list (
                                netstring.decode (children)
                                )
                        for child in children:
                                subject, name = tuple (
                                        netstring.decode (child)
                                        )
                                if subject:
                                        context = model[0]
                                else:
                                        context = subject = model[0]
                                joined = PNS_XML_continuation (
                                        self.pns_dom, child
                                        )
                                joined.pns_context = model[3]
                                self.pns_dom.pns_statement (
                                        (subject, name, ''), context,
                                        joined.pns_to_xml_unicode
                                        )
                                joined.finalization = self

        def pns_to_xml_unicode_a (self, resolved, model):
                if model[4] != ('_') or model[2] == '':
                        return False
                
                self.pns_contexts = {}
                question = resolved[:2]
                for co in netstring.decode (model[2]):
                        c, o = netstring.decode (co) # TODO? fix this
                        self.pns_to_xml_unicode (
                                resolved, question+(o, c, '_')
                                )
                        self.pns_contexts[c] = self.xml_parsed
                self.xml_parsed = None
                return False

class PNS_XML (finalization.Finalization):
        
        xml_type = xml_dom.Element
        xml_types = {}
        xml_unicoding = True
        xml_root = None
        
        pns_name = pns_statement = None
        
        def __init__ (self, prefixes=None, pi=None):
                self.xml_prefixes = prefixes or {}
                self.xml_pi = pi or {}
                
        def pns_to_xml (self, name, subject, context, statement):
                "rollback XML from PNS"
                self.pns_name = context
                self.pns_statement = statement
                self.pns_resolved = (subject, name, '')
                finalized = PNS_XML_continuation (self, None)
                if self.xml_unicoding:
                        statement (
                                self.pns_resolved, context,
                                finalized.pns_to_xml_unicode 
                                )
                else:
                        statement (
                                self.pns_resolved, context, 
                                finalized.pns_to_xml_utf8 
                                )
                finalized.finalization = self.pns_to_xml_continue
                        
        def pns_to_xml_continue (self, finalized):
                "PNS/XML rolledback"
                assert None == loginfo.log (
                        '%r' % finalized.xml_parsed, 'debug'
                        )
                e = finalized.xml_parsed
                if e and e.xml_valid != None:
                        e.xml_valid (self)
                self.xml_root = e
                self.pns_statement = None

        def xml_to_pns (self, context, statement):
                "commit XML to PNS"
                self.pns_name = context
                self.pns_statement = statement
                if self.xml_unicoding:
                        self.xml_unicode_to_pns (self.xml_root, context)
                else:
                        self.xml_utf8_to_pns (self.xml_root, context)
                self.pns_statement = None
                        
        def xml_unicode_to_pns (self, element, context):
                try:
                        pns = element.xml_attributes.pop (u'pns')
                except:
                        element.pns_name = ''
                        subject = context
                else:
                        element.pns_name = subject = pns.encode ('utf-8')
                if element.xml_children:
                        for child in element.xml_children:
                                self.xml_unicode_to_pns (child, subject)
                self.pns_statement ((
                        subject, element.xml_name.encode ('utf-8'),
                        netstring.encode (xml_unicode_to_pns (element))
                        ), context, self.xml_to_pns_continue)
                if subject != context:
                        element.xml_attributes[u'pns'] = pns
                        
        def xml_utf8_to_pns (self, element, context):
                try:
                        element.pns_name = subject = \
                                element.xml_attributes.pop ('pns')
                except:
                        element.pns_name = ''
                        subject = context
                if element.xml_children:
                        for child in element.xml_children:
                                self.xml_utf8_to_pns (child, subject)
                self.pns_statement ((
                        subject, element.xml_name,
                        netstring.encode (xml_utf8_to_pns (element)),
                        ), context, self.xml_to_pns_continue)
                if subject != context:
                        element.xml_attributes['pns'] = subject
                        
        def xml_to_pns_continue (self, resolved, model):
                # handle all XML to PNS responses, 
                assert None == loginfo.log (netstring.encode (model))
                if self.pns_resolved == resolved:
                        pass 
                        # this is the end, at least if the PNS peer does
                        # handle each of the statement in sequence, not
                        # answering the last one before the others.
                return False
        
        # note that it makes absolutely no sense to use a PNS_articulator
        # to commit or rollback a PNS/XML document object level: that DOM
        # allready a cache in itself (and the articulator is a cache too).
        #
        # note also that an PNS_XML instance is a finalization, so that
        # you may parse an XML tree with PNS names transfert its root to
        # a PNS_XML instance, articulate that DOM to the metabase and drop
        # its reference. when the PNS/TCP client releases its last reference
        # to the xml_to_pns_continue method of that DOM, the instance is
        # finalization ... with whatever finalization attached.
        #
        # so, practically, you don't need to subclass PNS_XML setting its
        # finalization is enough to program the continuations of commit
        # and rollback (it works pretty much the same, but with the support
        # of PNS_XML_continuations, which is even longer to explain so I
        # don't bother, sorry ;-)


def statement_utf8 (model, prefixes):
        e, children = pns_to_xml_utf8 (model)
        if children:
                e.xml_children = []
                for child in netstring.decode (children):
                        subject, name = netstring.decode (child)
                        if subject:
                                e.xml_children.append ('<%s pns="%s"/>' % (
                                        ''.join (xml_utf8.xml_prefix_FQN (
                                                name, prefixes
                                                )),
                                        xml_utf8.xml_attr (subject)
                                        ))
                        else:
                                e.xml_children.append (
                                        '<%s />' % xml_utf8.xml_prefix_FQN (
                                                name, prefixes
                                                )
                                        )
        return xml_utf8.xml_prefixed (
                e, prefixes, 
                ' context="%s"' % xml_utf8.xml_attr (model[3])
                )

def statements_utf8 (model, prefixes, contexts):
        for co in netstring.decode (model[2]):
                c, o = netstring.decode (co)
                if c not in contexts:
                        continue
                
                for more in statement_utf8 (
                        (model[0], model[1], o, c, '_'), prefixes, encoding
                        ):
                        yield more


def statement_unicode (model, prefixes, encoding='ASCII'):
        e, children = pns_to_xml_unicode (model)
        if children:
                e.xml_children = []
                for child in netstring.decode (children):
                        subject, name = netstring.decode (child)
                        if subject:
                                e.xml_children.append ('<%s pns="%s"/>' % (
                                        ''.join (xml_unicode.xml_prefix_FQN (
                                                unicode (name, 'utf-8'), 
                                                prefixes, encoding
                                                )),
                                        xml_unicode.xml_attr (
                                                unicode (subject, 'utf-8'), 
                                                encoding
                                                )
                                        ))
                        else:
                                e.xml_children.append (
                                        '<%s%s'
                                        ' />' % xml_unicode.xml_prefix_FQN (
                                                unicode (name, 'utf-8'), 
                                                prefixes, encoding
                                                )
                                        )
        return xml_unicode.xml_prefixed (
                e, prefixes, 
                ' context="%s"' % xml_unicode.xml_attr (
                        unicode (model[3], 'utf-8'), encoding
                        ), encoding
                )

def statements_unicode (model, prefixes, contexts, encoding='ASCII'):
        for co in netstring.decode (model[2]):
                c, o = netstring.decode (co)
                if c not in contexts:
                        continue
                
                for more in statement_unicode (
                        (model[0], model[1], o, c, '_'), prefixes, encoding
                        ):
                        yield more        

# Two helper functions to map a PNS name and its SAT to XML: 
#
# <public names="5:Names,6:Public,">
#   <public>Names</public>
#   <public>Public</public>
# </public>
#
# Something easy to transform with XSLT and present with CSS.

def name_utf8 (name, tag='public'):
        names = tuple (netstring.decode (name)) or (name,)
        if len (names) > 1:
                return '<%s names="%s">%s</%s>' % (
                        tag,
                        xml_utf8.xml_attr (name), 
                        ''.join ([name_utf8 (n, tag) for n in names]),
                        tag
                        )

        return '<%s>%s</%s>' % (tag, xml_tf8.xml_cdata (name), tag)


def name_unicode (name, tag='public', encoding='ASCII'):
        names = tuple (netstring.decode (name)) or (name,)
        if len (names) > 1:
                return '<%s names="%s">%s</%s>' % (
                        tag,
                        xml_unicode.xml_attr (unicode (name, 'UTF-8')), 
                        ''.join ([name_unicode (
                                n, tag, encoding
                                ) for n in names]),
                        tag
                        )

        return '<%s>%s</%s>' % (
                tag, xml_unicode.xml_cdata (unicode (name, 'UTF-8')), tag
                )


# Note about this implementation 
#
# it may be possible to get rid of the last level of PNS/XML articulation
# and make articulation sparser, by allowing un-named child element to
# be completely encoded in their parent. Yet this practically makes encoding
# from XML to PNS also more complex to support sensible trunking.
#
# Most XML leaf elements do not require a PNS/XML statement but the
# presence of one too large in their midst suppose a more elaborated
# algorithm for sparse articulation, counting every bytes in the parent's
# PNS/XML statement to decide which elements to "inline" as:
#
#         :subject,:name,::attributes,:first,:follow,,
#
# and which to reference only:
#
#         :subject,:name,:,
#
# it just might not be worth the trouble.
#
# TODO: add a depth limit to PNS_XML, avoid the possible infinite loop 
#       when there is a circular PNS/XML statement in the metabase for
#       the articulated XML element tree.