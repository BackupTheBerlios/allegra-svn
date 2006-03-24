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
        xml_dom, xml_unicode, pns_sat, pns_xml, pns_articulator,
        presto, presto_pns, presto_http
        )


# PNS/REST interface

def pns_handle_rest (component, reactor):
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
        # on success. this function is applied by all PNS/REST methods
        # to handle the same part of their process.
        #
        if not reactor.presto_vector:
                return '<pns:articulate/>'
        
        context = reactor.presto_vector.get (u'context', u'').encode ('UTF-8')
        if not context:
                return '<pns:articulate/>'
        
        if component.pns_client == None:
                metabase = component.xml_attributes.setdefault (
                        u'metabase', u'127.0.0.1:3534'
                        ).encode ('ASCII', 'ignore')
                try:
                        host, port = metabase.split (':')
                except:
                        component.pns_client = component.PNS_CLIENT (
                                (metabase, 3534), component.pns_peer
                                )
                else:
                        component.pns_client = component.PNS_CLIENT (
                                (host, int (port)), component.pns_peer
                                )
                if component.pns_client == None:
                        return '<pns:tcp-error/>'
                
                component.xml_dom = reactor.presto_dom
        predicate = reactor.presto_vector.get (
                u'predicate', u'sat'
                ).encode ('UTF-8')
        lang = reactor.presto_vector.get (u'lang')
        if lang:
                component.pns_sat_language = pns_sat.language (
                        lang.encode ('UTF-8')
                        )
        else:
                component.pns_sat_language = pns_sat.language ()
        articulated = []
        name = pns_sat.articulate_re (
                context, articulated.append, component.pns_sat_language
                )
        if not name:
                return '<pns:articulate/>'

        return (articulated, name, predicate)


# PNS/REST articulate

class PNS_articulate_xml (finalization.Finalization):
        
        xml_name = u'http://pns/ articulate'
        xml_first = u''
        xml_parent = xml_attributes = xml_follow = None
                
        def __init__ (
                self, name, articulator, predicate,
                prefixes={}, types={}, type=xml_dom.XML_element
                ):
                self.pns_statement = articulator.pns_question
                self.pns_question = (name, predicate, '')
                self.xml_prefixes = prefixes
                self.xml_type = type
                self.xml_types = types
                self.xml_children = []
                articulator.pns_command (
                        ('', '', name), self.pns_resolve_index
                        )
                articulator.pns_command (
                        ('', name, ''), self.pns_resolve_context
                        )
                        
        def pns_resolve_index (self, resolved, model):
                if model == None:
                        return
                
                self.xml_children.append (
                        pns_xml.name_unicode (model[0], 'pns:index')
                        ) # TODO? resolve SAT or leave it bare ...
        
        def pns_resolve_context (self, resolved, model):
                if model == None:
                        return
                
                for context in model[1]:
                        self.xml_children.append (
                                pns_xml.name_unicode (context, 'pns:context')
                                ) # TODO? resolve SAT or leave it bare ...
                #
                finalized = pns_xml.PNS_XML_continuations (
                        self, self.pns_question[:2]
                        )
                self.pns_statement (
                        self.pns_question, '', finalized.pns_to_xml_unicode_a
                        )
                finalized.finalization = self.pns_xml_continue

        def pns_xml_continue (self, finalized):
                if finalized.pns_contexts == None:
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


class PNS_articulate_rest (producer.Stalled_generator):
        
        def __call__ (self, finalized):
                self.generator = xml_unicode.xml_prefixed (
                        finalized, finalized.xml_prefixes
                        )
                                
def articulate (component, reactor):
        rest = pns_handle_rest (component, reactor)
        try:
                articulated, context, predicate = rest
        except:
                return rest
        
        text = reactor.presto_vector.pop (u'text', None)
        if not text:
                # load the PNS/XML elements from the metabase and include
                # the result tree in the REST response.
                #
                react = PNS_articulate_rest ()
                PNS_articulate_xml (
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
        else:
                xml_utf8.transcode (root)
        return root # returns an XML element ...
        

def articulate_new (component, reactor):
        #
        # clear the articulator's cache, if any
        #
        component.pns_commands = {}
        component.pns_contexts = {}
        return '<pns:articulate-new/>'


# PNS/REST search

class PNS_search_xml (finalization.Finalization):
        
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

class PNS_search_rest (producer.Stalled_generator):
        
        def __call__ (self, finalized):
                self.generator = iter (finalized.xml_children)                                
        
def search (component, reactor):
        rest = pns_handle_rest (component, reactor)
        try:
                articulated, name, predicate = rest
        except:
                return rest
        
        react = PNS_search_rest ()
        PNS_search_xml (
                name, component, predicate,
                prefixes=reactor.presto_dom.xml_prefixes
                ).finalization = react
        return react


# PRESTo Component Declaration

# PNS/REST articulator

class PNS_REST (
        presto.PRESTo_async, pns_articulator.PNS_articulator
        ):
        
        xml_name = u'http://pns/ rest'

        def __init__ (self, name, attr):
                self.xml_attributes = attr or {}

        def xml_valid (self, dom):
                dom.xml_prefixes['http://pns/'] = 'pns'
                dom.xml_prefixes['http://presto/'] = 'presto'
                #
                self.pns_commands = {}
                self.pns_contexts = {}
                self.pns_client = None
                #
                #metabase = self.xml_attributes.setdefault (
                #        u'metabase', u'127.0.0.1:3534'
                #        ).encode ('ASCII', 'ignore')
                #try:
                #        host, port = metabase.split (':')
                #except:
                #        pns_articulator.PNS_articulator.__init__ (
                #                self, (metabase, 3534)
                #                )
                #else:
                #        pns_articulator.PNS_articulator.__init__ (
                #                self, (host, int (port))
                #                )

        pns_peer = presto_pns.pns_peer
        
        presto = presto_http.form_rest
                        
        presto_interfaces = set ((
                u'PRESTo', u'context', u'text', u'lang', u'predicate'
                ))

        presto_methods = {u'articulate': articulate}
        

presto_components = (PNS_REST, )

if __debug__:
        from allegra.presto_prompt import presto_debug_async
        presto_debug_async (PNS_REST)