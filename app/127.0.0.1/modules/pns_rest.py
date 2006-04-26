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

from allegra import (
        netstring, loginfo, finalization, producer, 
        xml_dom, xml_unicode, pns_model, 
        pns_sat, pns_xml, pns_articulator,
        presto, presto_pns, presto_http
        )


# PNS/REST feed XML from HTTP

class Feed_xml_reactor (producer.Stalled_generator):

        def __init__ (self, dom):
                self.pns_xml_dom = dom
        
        def __call__ (self, finalized):
                self.generator = iter (('<pns:feed-http-xml/>', ))
                                

def feed_http_xml (
        component, url, xml_types={}, xml_type=pns_xml.Articulate
        ):
        host, port, urlpath = http_client.RE_URL.match (url).groups ()
        dom = xml_reactor.XML_collector (unicoding=0)
        pns_xml.articulate (dom, url, xml_types, xml_type, statement)
        request = http_client.GET (http_client.HTTP_client (
                ) (host, int (port or '80')), urlpath) (dom)
        react = Feed_xml_reactor (dom)
        request.finalization = react
        return react


# PNS/REST articulate

def articulate_rest (component, reactor):
        #
        # handle the beginning of any PNS/REST request: 
        #
        # 1. check that there is something to articulate
        # 2. attribute a PNS/TCP client if there is none available
        # 3. decode the request's text, language and predicate
        # 4. articulate a name for the context articulated
        #
        # and either return an XML string on error or a tuple:
        #
        #        (articulated, name, predicate)
        #
        # on success.
        #
        if component.pns_client == None and not presto_pns.pns_open (
                component, reactor
                ):
                return '<pns:tcp-error/>'
                
        vector = reactor.presto_vector
        context = vector.setdefault (u'context', u'').encode ('UTF-8')
        if not context:
                return '<pns:articulate/>'
        
        predicate = vector.setdefault (u'predicate', u'sat').encode ('UTF-8')
        field = set ()
        name = pns_model.pns_name (context, field)
        if name == context and len (field) > 1:
                # Public Names
                return ((), context, predicate)
        
        # Articulated
        lang = vector.get (u'lang')
        if lang:
                component.pns_sat_language = pns_sat.language (
                        lang.encode ('UTF-8')
                        )
        elif component.pns_sat_language == None:
                component.pns_sat_language = pns_sat.language ()
        articulated = []
        name = pns_sat.articulate_re (
                context, articulated.append, component.pns_sat_language
                )
        if not name:
                return '<pns:articulate/>'

        return (articulated, name, predicate)


class Articulate_xml (finalization.Finalization):
        
        xml_name = u'http://pns/ articulate'
        xml_first = u''
        xml_parent = xml_attributes = xml_follow = None
        
        pns_contexts = None
                
        def __init__ (
                self, name, articulator, predicate,
                prefixes={}, types={}, type=xml_dom.XML_element
                ):
                self.pns_statement = articulator.pns_question
                self.pns_command = articulator.pns_command
                self.pns_question = (name, predicate, '')
                self.xml_prefixes = prefixes
                self.xml_type = type
                self.xml_types = types
                self.xml_children = []
                finalized = pns_xml.PNS_XML_continuations (
                        self, (name, predicate)
                        )
                self.pns_statement (
                        self.pns_question, '', finalized.pns_to_xml_unicode_a
                        )
                finalized.finalization = self.pns_xml_continue
                        
        def pns_xml_continue (self, finalized):
                if finalized.pns_contexts == None:
                        self.pns_command (
                                ('', self.pns_question[0], ''), 
                                self.pns_resolve_context
                                )
                        return
                
                for context, e in finalized.pns_contexts.items ():
                        if e.xml_valid:
                                e.xml_valid (self)
                        if e.xml_attributes:
                                e.xml_attributes[u'context'] = unicode (
                                        context, 'UTF-8'
                                        )
                        else:
                                e.xml_attributes = {u'context': unicode (
                                        context, 'UTF-8'
                                        )}
                        self.xml_children.append (e)

        def pns_resolve_context (self, resolved, model):
                if model != None:
                        self.pns_contexts = model[1]
                        for context in model[1]:
                                self.xml_children.append (
                                        pns_xml.name_unicode (
                                                context, 'pns:context'
                                                )
                                        )
                self.pns_command (
                        ('', '', self.pns_question[0]), 
                        self.pns_resolve_index
                        )


        def pns_resolve_index (self, resolved, model):
                if model == None:
                        return
                
                self.xml_children.append (
                        pns_xml.name_unicode (model[0], 'pns:index')
                        )
                if self.pns_contexts == None:
                       return
                
                for name in model[1]:
                        if len (tuple (netstring.decode (name))) == 0:
                                continue
                        
                        self.pns_statement (
                                (name, 'sat', ''), '', self.pns_resolve_sat
                                )
        
        def pns_resolve_sat (self, resolved, model):
                if model[2]:
                        self.xml_children.append (''.join (
                                pns_xml.statements_unicode (
                                        model, self.xml_prefixes, 
                                        self.pns_contexts
                                        )
                                ))

                
class Articulate_xml_reactor (producer.Stalled_generator):
        
        # the PRESTo response's reactor
        
        def __call__ (self, finalized):
                self.generator = xml_unicode.xml_prefixed (
                        finalized, finalized.xml_prefixes
                        )
                                
def articulate_xml (component, reactor):
        rest = articulate_rest (component, reactor)
        try:
                articulated, context, predicate = rest
        except:
                return rest
        
        text = reactor.presto_vector.pop (u'text', None)
        if not text:
                # load the PNS/XML elements from the metabase and include
                # the result tree in the REST response.
                #
                react = Articulate_xml_reactor ()
                Articulate_xml (
                        context, component, predicate,
                        prefixes=reactor.presto_dom.xml_prefixes
                        ).finalization = react
                return react # returns a stalled reactor ...
                
        # articulate text as a PNS/XML or PNS/SAT statement in the
        # context submitted and return the root element as result.
        #
        pns_statement = component.pns_statement
        root = pns_xml.articulate (
                xml_dom.XML_dom ({
                        'http://www.w3.org/XML/1998/namespace': 'xml'
                        }), context, {}, pns_xml.Articulate, pns_statement
                ).xml_parse_string (text)
        if root == None:
                # if the text is not a valid XML document, articulate PNS/SAT 
                # statements and provide a PNS/XML <sat/> element as response.
                subject = pns_sat.articulate_re (
                        text.encode ('UTF-8'), articulated.append, 
                        component.pns_sat_language
                        )
                for (l, f, t, n) in articulated:
                        pns_statement ((n, 'sat', t, context))
                root = xml_dom.XML_element (
                        u'sat', {u'pns': unicode (
                                subject, 'UTF-8', 'xmlcharrefreplace'
                                )}
                        )
                root.xml_first = text
                #
                # note that this is a rather CPU intensive process that
                # would better be moved to an asynchronous XML collector
                # like the one used for RSS feeds. Chunking the imput
                # stream in 4096 bytes ensure a non-blocking behaviour
                # from the web peer.
        else:
                xml_utf8.transcode (root)
        return root # returns an XML element ...
        

def articulate_new (component, reactor):
        #
        # clear the articulator's cache, if any
        #
        if __debug__ and component.pns_client != None:
                component.pns_client.handle_close ()
        component.pns_commands = {}
        component.pns_contexts = {}
        return '<pns:articulate-new/>'


# PNS/REST search

class Search_xml (finalization.Finalization):
        
        # a PNS_search, XML_element *and* XML_dom implementation
        
        xml_name = u'http://pns/ search'
        xml_first = u''
        xml_parent = xml_attributes = xml_follow = None
        
        # names *are* interfaces in Python *~)
        
        def __init__ (
                self, name, articulator, predicate, prefixes, HORIZON=68
                ):
                self.pns_contexts = set ()
                self.pns_name = name
                self.pns_predicate = predicate
                self.xml_prefixes = prefixes
                self.xml_children = []
                self.pns_statement = articulator.pns_client.pns_statement
                pns_articulator.PNS_walk (
                        name, articulator, self.pns_walk_out, HORIZON
                        ).finalization = self
        
        def pns_walk_out (self, subject, contexts):
                self.pns_contexts.update (contexts)
                self.pns_statement (
                        (subject, self.predicate, ''), '', 
                        finalized.pns_resolve_statements
                        )
                        
        def pns_resolve_statements (resolved, model):
                self.xml_children.append (''.join (
                        pns_xml.statements_unicode (
                                model, self.xml_prefixes
                                )
                        ))

class Search_xml_reactor (producer.Stalled_generator):
        
        def __call__ (self, finalized):
                self.generator = iter (finalized.xml_children)                                
        
def search_xml (component, reactor):
        rest = articulate_rest (component, reactor)
        try:
                articulated, name, predicate = rest
        except:
                return rest
        
        react = Search_xml_reactor ()
        Search_xml (
                name, component, predicate,
                prefixes=reactor.presto_dom.xml_prefixes
                ).finalization = react
        return react

# PNS/REST component

class PNS_REST (
        presto.PRESTo_async, pns_articulator.PNS_articulator
        ):
        
        xml_name = u'http://pns/ rest'

        def __init__ (self, name, attr):
                self.xml_attributes = attr or {}

        def xml_valid (self, dom):
                dom.xml_prefixes['http://pns/'] = 'pns'
                dom.xml_prefixes['http://presto/'] = 'presto'
                self.pns_commands = {}
                self.pns_contexts = {}
                self.pns_client = None

        pns_peer = presto_pns.pns_peer
        
        presto = presto_http.form_rest
        
        presto_interfaces = set ((
                u'PRESTo', 
                u'subject', u'predicate', u'object', u'context', 
                u'text', u'lang', 
                ))

        presto_methods = {
                u'pns': presto_pns.pns_statement,
                u'search': search_xml,
                u'articulate': articulate_xml,
                u'clear': articulate_new,
                }
        
        pns_sat_language = None

presto_components = (PNS_REST, )

if __debug__:
        from allegra.presto_prompt import presto_debug_async
        presto_debug_async (PNS_REST)
        
#
# GET ?context= HTTP/1.1 
# GET ?context=&predicate= HTTP/1.1 
# GET ?context=&subject=&predicate HTTP/1.1 
# GET ?context=&subject=&predicate=&object= HTTP/1.1 
# POST ?context=&subject=&predicate=&object= HTTP/1.1 
# POST <?xml version="1.0" encoding="UTF-8"> ...
#
# <presto:PRESTo>...</presto:PRESTo>
#
# GET /xml?context= HTTP/1.1
#
# <pns:articulated pns="name">
#   <pns:sat pns="5:Names,6:Public," context="...">Public Names</pns:sat>
#   <pns:sat ... >...</pns:sat>
#   <pns:context names=""/>
#   <pns:index names=""/>
# </pns:articulated>
#
# Ask a question for every articulated index and 