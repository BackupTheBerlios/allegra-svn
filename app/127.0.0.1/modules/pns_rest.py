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
        netstring, loginfo, finalization, 
        producer, xml_dom, xml_unicode,
        pns_sat, pns_xml, pns_articulator,
        presto_pns, presto_http
        )


# PNS/REST interface

def pns_get_rest (component, reactor):
        "search for context(s)"
        if not reactor.presto_vector:
                return '<presto:pns-articulate/>'
        
        if component.pns_client == None:
                if component.pns_open (reactor):
                        component.pns_articulator = \
                                pns_articulator.PNS_articulator (
                                        component.pns_client
                                        )
                else:
                        return '<presto:pns-tcp-error/>'
                        
        elif component.pns_articulator == None: 
                component.pns_articulator = pns_articulator.PNS_articulator (
                        component.pns_client
                        )
        context = reactor.presto_vector.get (u'context', u'').encode ('UTF-8')
        if not context:
                return '<presto:pns-articulate/>'
        
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
                return '<presto:pns-articulate/>'

        return (articulated, name, predicate)


# PNS/REST articulate

class PNS_articulate_xml (finalization.Finalization):
        
        xml_name = u'http://allegra/ pns-articulate'
        xml_first = u''
        xml_parent = xml_attributes = xml_follow = None
                
        def __init__ (
                self, name, articulator, predicate,
                prefixes={}, types={}, type=xml_dom.XML_element
                ):
                self.pns_name = name
                self.pns_statement = articulator.pns_client.pns_statement
                self.pns_question = (name, predicate, '')
                self.xml_prefixes = prefixes
                self.xml_type = type
                self.xml_types = types
                self.xml_children = []
                articulator.pns_command (
                        ('', name, ''), self.pns_resolve_context
                        )
        
        def pns_resolve_context (self, resolved, model):
                loginfo.log ('pns_resolve_context %r' % (model,), 'debug')
                if model == None:
                        return
                
                for context in model[1]:
                        finalized = pns_xml.PNS_XML_continuation (
                                self, self.pns_question
                                )
                        self.pns_statement (
                                self.pns_question, context, 
                                finalized.pns_to_xml_unicode 
                                )
                        finalized.finalization = self.pns_xml_continue

        def pns_xml_continue (self, finalized):
                loginfo.log ('pns_xml_continue %r' % finalized, 'debug')
                e = finalized.xml_parsed
                if e:
                        if e.xml_valid:
                                e.xml_valid (self)
                        self.xml_children.append (e)


class PNS_articulate_rest (producer.Stalled_generator):
        
        "the articulation's finalization"
        
        def __call__ (self, finalized):
                loginfo.log ('PNS_articulate_rest %r' % finalized, 'debug')
                self.generator = xml_unicode.xml_prefixed (
                        finalized, finalized.xml_prefixes
                        )
                                

def articulate_get (component, reactor):
        rest = pns_get_rest (component, reactor)
        try:
                articulated, name, predicate = rest
        except:
                return rest
        
        loginfo.log ('articulate_get', 'debug')
        react = PNS_articulate_rest ()
        PNS_articulate_xml (
                name, component.pns_articulator, predicate,
                prefixes=reactor.presto_dom.xml_prefixes
                ).finalization = react
        return react
        

def articulate_post (component, reactor):
        pass

def articulate_new (component, reactor):
        "clear the articulator's cache, if any"
        component.pns_articulator = None
        return '<presto:pns-articulate-new/>'


# PNS/REST search

class PNS_search_xml (finalization.Finalization):
        
        # a PNS_search, XML_element *and* XML_dom implementation
        
        xml_name = u'http://allegra/ search'
        xml_first = u''
        xml_parent = xml_attributes = xml_follow = None
        
        # names *are* interfaces in Python *~)
        
        def __init__ (
                self, name, articulator, predicate, HORIZON=68,
                prefixes={}, types={}, type=xml_dom.XML_element
                ):
                self.pns_contexts = set ()
                self.pns_name = name
                self.pns_predicate = predicate
                self.xml_prefixes = prefixes
                self.xml_type = type
                self.xml_types = types
                self.xml_children = []
                self.pns_statement = articulator.pns_client.pns_statement
                pns_articulator.PNS_walk (
                        name, articulator, self.pns_walk_out, HORIZON
                        ).finalization = self
        
        def pns_walk_out (self, subject, contexts):
                self.pns_contexts.update (contexts)
                question = (subject, self.pns_predicate, '')
                for context in contexts:
                        finalized = pns_xml.PNS_XML_continuation (
                                self, question
                                )
                        self.pns_statement (
                                question, context, 
                                finalized.pns_to_xml_unicode 
                                )
                        finalized.finalization = self.pns_xml_continue

        def pns_xml_continue (self, finalized):
                e = finalized.xml_parsed
                if e:
                        if e.xml_valid:
                                e.xml_valid (self)
                        self.xml_children.append (e)


class PNS_search_rest (producer.Stalled_generator):
        
        "the PNS/REST search's finalization"
        
        def __call__ (self, finalized):
                self.generator = xml_unicode.xml_prefixed (
                        finalized, finalized.xml_prefixes
                        )
                                
        
def search (component, reactor):
        rest = pns_get_rest (component, reactor)
        try:
                articulated, name, predicate = rest
        except:
                return rest
        
        react = PNS_search_rest ()
        PNS_search_xml (
                name, component.pns_articulator, predicate,
                prefixes=reactor.presto_dom.xml_prefixes
                ).finalization = react
        return react


# PRESTo Component Declaration

class PNS_REST (presto_pns.PNS_session):

        xml_name = u'http://allegra/ pns-rest'
        
        pns_articulator = None
        
        presto = presto_http.get_rest
                        
        presto_interfaces = set ((
                u'PRESTo', 
                u'subject', u'predicate', u'object', u'context', 
                u'lang',
                ))

        presto_methods = {
                u'pns': presto_pns.pns_statement,
                u'search': search,
                u'articulate': articulate_get,
                u'clear': articulate_new,
                }


presto_components = (PNS_REST, )

if __debug__:
        from allegra.presto_prompt import presto_debug_async
        presto_debug_async (PNS_REST)