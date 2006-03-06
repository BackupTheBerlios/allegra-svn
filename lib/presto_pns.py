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
        netstring, loginfo, finalization, producer, 
        pns_model, pns_sat, pns_xml, pns_client, pns_articulator, 
        presto, presto_http
        )


# PRESTo/PNS Component Object Model

class PRESTo_dom (
        pns_xml.PNS_XML, loginfo.Loginfo, finalization.Finalization
        ):
        
        "PNS/XML implementation of PRESTo's COM interfaces"
        
        xml_name = 'http://presto/ component'

        presto_defered = None
        
        def __init__ (self, name, types={}, type=presto.PRESTo_async):
                self.xml_prefixes = {u'http://presto/': u'presto'}
                self.xml_pi = {}
                self.xml_type = type
                self.xml_types = types
                self.presto_name = name
                        
        def __repr__ (self):
                return 'presto-pns-dom name="%s"' % self.presto_name
        
        # The PRESTo commit and rollback interfaces
        
        def presto_rollback (self, defered): 
                # yes I use defered too (but just a list is enough to 
                # implement them, thank you ;-)
                #
                if self.presto_defered:
                        try:
                                self.presto_defered.append (defered)
                        except:
                                return False
                        
                else:
                        self.presto_defered = [defered]
                        self.pns_to_xml (
                                self.xml_name, 
                                self.presto_name, 
                                self.presto_root.presto_host,
                                self.pns_client.pns_statement
                                )
                return True
        
        def presto_commit (self, defered):
                if self.presto_defered:
                        return False
                
                self.presto_defered = (defered, )
                self.xml_to_pns (
                        self.presto_name, 
                        self.presto_root.presto_host,
                        self.pns_client.pns_statement
                        )
                return True
        

# PNS/REST client component and methods

class PNS_statement (producer.Stalled_generator):
        
        def __init__ (self, dom, encoding='ASCII'):
                self.xml_dom = dom
                self.encoding = encoding
        
        def __call__ (self, resolved, model):
                self.generator = pns_xml.pns_to_xml_unicode_strings (
                        self.xml_dom, model, self.encoding
                        )
                return False

        # a fine example of a Stalled_generator application, producing
        # the prefixed and encoded XML string for any PNS response, but
        # stalling the HTTP response producer until the question is resolved 
        # by a PNS/TCP client or an articulator.
        #
        # note how the same instance holds state for the stalled HTTP 
        # response *and* serves as a handler for the PNS/TCP question.
                                
                        
class PNS_command (producer.Stalled_generator):
        
        def __call__ (self, resolved, model):
                if resolved[1] == '':
                        if model:
                                self.generator = iter ((
                                        pns_xml.public_unicode (
                                                model[0], 'presto:index'
                                                ),
                                        ))
                        else:
                                self.generator = iter ((
                                        '<presto:index name=""/>',
                                        ))
                elif resolved[2] == '':
                        if model:
                                self.generator = (
                                        pns_xml.public_unicode (
                                                context, 'presto:context'
                                                ) 
                                        for context in model[1]
                                        )
                        else:
                                self.generator = iter ((
                                        '<presto:context name=""/>',
                                        ))
                else:
                        self.generator = iter (('<presto:graph/>',))
                return False
                        

def pns_statement (component, reactor):
        "pass-through method for PNS/TCP statements"
        if not reactor.presto_vector:
                return '<presto:presto/>'
        
        if component.pns_client == None and not component.pns_open (reactor):
                return '<presto:pns-tcp-error/>'
                
        model = (
                reactor.presto_vector.setdefault (
                        u'subject', u''
                        ).encode ('UTF-8'),
                reactor.presto_vector.setdefault (
                        u'predicate', u''
                        ).encode ('UTF-8'),
                reactor.presto_vector.setdefault (
                        u'object', u''
                        ).encode ('UTF-8')
                )
        context = reactor.presto_vector.setdefault (
                u'context', u''
                ).encode ('UTF-8')
        if '' == model[0]:
                if '' == model[1] == model[2]:
                        if context:
                                # subscriptions: quit
                                component.pns_client.pns_quit (
                                        context, component.pns_log
                                        )
                        else:
                                # filter-out PNS/TCP close, of course.
                                return '<presto:presto/>'
                        
                else:
                        # PNS/Inference command
                        react = PNS_command ()
                        component.pns_client.pns_command (model, react)
                        return react
                        
        elif '' == model[1] and model[0] == context:
                # subscriptions: join or subscribe
                if model[2]:
                        component.pns_client.pns_join (
                                context, model[2], component.pns_log
                                )
                else:
                        component.pns_client.pns_subscribe (
                                context, component.pns_log
                                )
        else:
                # questions and answers
                react = PNS_statement (reactor.presto_dom)
                component.pns_client.pns_statement (model, context, react)
                return react


class PNS_session (presto.PRESTo_async):
        
        xml_name = u'http://presto/ pns'
        
        PNS_CLIENT = pns_client.PNS_client ()

        pns_client = None

        def xml_valid (self, dom):
                dom.xml_prefixes['http://presto/'] = 'presto'
                if self.xml_attributes == None:
                        self.xml_attributes = {}
        
        def pns_open (self, reactor):
                metabase = self.xml_attributes.setdefault (
                        u'metabase', u'127.0.0.1:3534'
                        ).encode ('ASCII', 'ignore')
                try:
                        host, port = metabase.split (':')
                except:
                        channel = self.PNS_CLIENT (
                                (metabase, 3534), self.pns_peer
                                )
                else:
                        channel = self.PNS_CLIENT (
                                (host, int (port)), self.pns_peer
                                )
                if channel:
                        self.pns_client = channel
                        self.xml_dom = reactor.presto_dom
                        return True
                
                return False

        def pns_peer (self, resolved, model):
                ip = model[3]
                if ip:
                        self.xml_attributes[u'peer'] = unicode (ip, 'UTF-8')
                        return True # opened, keep this handler
                        
                self.pns_client = None
                try:
                        del self.xml_attributes[u'peer']
                except KeyError:
                        pass
                self.xml_dom = None # de-cycle on close, unload from cache!
                return False # closed, release this handler

        def pns_log (self, model):
                # TODO: move to a BSDDB queue ...
                s = ''.join (pns_xml.pns_to_xml_unicode_strings (
                        self.xml_dom.xml_prefixes, model
                        ))
                try:
                        self.pns_xml_log.append (s)
                except:
                        self.pns_xml_log = [s]
                
        presto_interfaces = set ((
                u'PRESTo', u'subject', u'predicate', u'object', u'context'
                ))

        presto = presto_http.get_rest
                        
        presto_methods = {None: pns_statement}
        

# PNS/REST Articulator

def pns_articulate_rest (finalized):
        "generates the REST for the finalized articulation"
        yield '<presto:articulate>'

        if finalized.pns_index:
                yield pns_xml.public_unicode (
                        finalized.pns_index, 'pns:index'
                        )
                        
        for subject, statements in finalized.pns_subjects:
                yield '<presto:subject>'
        
                yield pns_xml.public_unicode (subject, 'pns:index')
        
                for model in statements:
                        yield pns_xml.pns_xml_unicode (
                                model, pns_xml.pns_cdata_unicode (model[2])
                                )
                                
                yield '</presto:subject>'
        
        if len (finalized.pns_contexts) > 0:
                for name in finalized.pns_contexts:
                        yield pns_xml.pns_names_unicode (name, 'pns:context')
                
        if len (finalized.pns_sat) > 0:
                for model in finalized.pns_sat:
                        yield pns_xml.pns_xml_unicode (
                                model, pns_xml.pns_cdata_unicode (model[2])
                                )
                                
        yield '</presto:articulate>'
                        
                        
class PNS_articulate (producer.Stalled_generator):
        
        "the articulation's finalization"
        
        def __call__ (self, finalized):
                self.generator = pns_articulate_rest (finalized)
                                

def pns_articulate (component, reactor):
        "articulate a context"
        text = reactor.presto_vector.get (u'articulated', u'').encode ('UTF-8')
        if not text:
                return '<presto:articulate/>'
        
        lang = reactor.presto_vector.get (u'lang')
        if lang:
                component.pns_sat_language = pns_sat.language (
                        lang.encode ('UTF-8')
                        )
        articulated = []
        name = pns_sat.articulate_re (
                text, articulated.append, component.pns_sat_language
                )
        if name:
                return '<presto:articulate/>'

        react = PNS_articulate ()
        pns_articulator.PNS_articulate (
                component.pns_articulator, name, netstring.netlist (
                        reactor.presto_vector[
                                u'predicates'
                                ].encode ('UTF-8') or 'sat'
                        )
                ).finalization = react
        return react
        

# Note about this implementation
#
# <presto:pns 
#        xmlns:presto="http://presto/"
#        metabase="127.0.0.1:3534" 
#        language="en"
#        >
#        <presto:subscription pns=""/>
# </presto:pns>