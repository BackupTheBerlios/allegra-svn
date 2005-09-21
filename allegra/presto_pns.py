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

from allegra.reactor import Buffer_reactor
from allegra.presto import PRESTo_async, PRESTo_reactor, presto_xml
from allegra.netstring import netstrings_decode, netstrings_encode 
from allegra import \
        pns_model, pns_sat, pns_xml, pns_client, pns_articulator


# Articulate a PNS/TCP session as XML and vic-versa from REST interfaces,
# and packages those interfaces in a reusable component for Allegra PRESTo.
#
# The PNS_presto is the base class to derive other articulators for
# distinct XML dialects (RSS, XHTML, etc ...). Theme, style or localization
# can be elaborated as component instances of those derived classes. But
# actually it is allways "just" XML markup and text strings articulated in
# and out of PNS.
#
# Eventually, the PNS_presto class can deliver practical component instance
# distribution by storing instance states to PNS and retrieving them from
# PNS too.
#

class PRESTo_statement (Buffer_reactor):
        
        def __call__ (self, resolved, model):
                self.buffer (pns_xml.pns_xml_unicode (
                        model, pns_xml.pns_cdata_unicode (model[2])
                        ))
                self.buffer ('')
                return False
                        
                        
class PRESTo_command (Buffer_reactor):
        
        def __call__ (self, resolved, model):
                if resolved[1] == '':
                        if model[1]:
                                self.buffer (pns_xml.pns_names_unicode (
                                        model[0], tag='pns:index', attr=''
                                        ))
                        else:
                                self.buffer ('<pns:index name=""/>')
                elif resolved[2] == '':
                        if len (model[1]) > 0:
                                self.buffer (''.join ([
                                        pns_xml.pns_names_unicode (
                                                context, tag='pns:context', 
                                                attr='' 
                                                ) 
                                        for context in model[1]
                                        ]))
                        else:
                                self.buffer ('<pns:context name=""/>')
                else:
                        self.buffer ('<pns:routes/>')
                self.buffer ('')
                return False
                        

class PRESTo_articulate_subject (Buffer_reactor):
        
        def __call__ (self, finalized):
                if len (finalized.pns_objects) == 0:
                        self.buffer ('<allegra:subject/>')
                        self.buffer ('')
                        return
                        
                del finalized.pns_articulator
                self.buffer ('<allegra:subject>')
                for model in finalized.pns_objects:
                        self.buffer (pns_xml.pns_xml_unicode (
                                model, pns_xml.pns_cdata_unicode (model[2])
                                ))
                self.buffer ('</allegra:subject>')
                self.buffer ('') # ... buffer_react ()
                                
                                
class PRESTo_articulate (Buffer_reactor):
        
        def __call__ (self, finalized):
                self.buffer ('<allegra:articulate>')
                if finalized.pns_index:
                        self.buffer (pns_xml.pns_names_unicode (
                                finalized.pns_index, tag='pns:index', attr=' '
                                ))
                for subject, statements in finalized.pns_subjects:
                        self.buffer ('<allegra:subject>')
                        self.buffer (pns_xml.pns_names_unicode (
                                subject, tag='pns:index', attr=' ' 
                                ))
                        for model in statements:
                                self.buffer (pns_xml.pns_xml_unicode (
                                        model, 
                                        pns_xml.pns_cdata_unicode (model[2])
                                        ))
                        self.buffer ('</allegra:subject>')
                if len (finalized.pns_contexts) > 0:
                        for name in finalized.pns_contexts:
                                self.buffer (pns_xml.pns_names_unicode (
                                        name, tag='pns:context', attr=' '
                                        ))
                if len (finalized.pns_sat) > 0:
                        for model in finalized.pns_sat:
                                self.buffer (pns_xml.pns_xml_unicode (
                                        model, 
                                        pns_xml.pns_cdata_unicode (model[2])
                                        ))
                self.buffer ('</allegra:articulate>')
                self.buffer ('') # ... buffer_react ()
                                

class PRESTo_articulator (
        PRESTo_async, pns_articulator.PNS_articulator
        ):
                 
        presto_interfaces = set ((
                u'PRESTo', 
                u'articulated', 
                u'subject', u'predicate', u'object', u'context'
                ))
                
        xml_name = u'http://allegra/ pns-articulator'

        # TODO: move the client management to a separate module class
        #       that implements a multiplexer of which and instance is
        #       attached to the presto_root.
        #
        #       presto_pns.py is an extension of PRESTo that provides
        #       also PNS persistence for XML component instances.
        #
        
        pns_client = pns_client.PNS_client_channel ()
        pns_client.tcp_connect ()
        
        #
        
        def xml_valid (self, dom):
                self.xml_dom = dom

        def presto_pns (self, reactor):
                if self.pns_client == None:
                        self.pns_client = pns_client.PNS_client_channel ()
                        self.pns_client.tcp_connect ()
                        return

                if reactor.presto_vector[u'subject']:
                        if (
                                reactor.presto_vector[u'context'] or 
                                reactor.presto_vector[u'predicate'] 
                                ):
                                return self.presto_pns_statement (reactor)

                        return self.presto_pns_protocol (reactor)
                        
                # commands
                return self.presto_pns_command (reactor)
                
        def presto_articulate (self, reactor):
                if self.pns_client == None:
                        self.pns_client = pns_client.PNS_client_channel ()
                        self.pns_client.tcp_connect ()
                        return

                articulated, horizon = self.presto_pns_validate (
                        reactor.presto_vector[u'articulated'].encode ('UTF-8')
                        )
                if not articulated:
                        return

                predicates = reactor.presto_vector[u'predicate'].encode ('UTF-8')
                if predicates:
                        predicates = netstrings_decode (predicates)
                else:
                        predicates = ('sat', )
                react = PRESTo_articulate ()
                pns_articulator.PNS_articulate (
                        self, articulated, predicates
                        ).finalization = react
                return react
                
        presto_methods = {
                u'pns': presto_pns, 
                u'articulate': presto_articulate, 
                }
                
        presto = presto_articulate
        
        def presto_pns_validate (self, encoded, context=''):
                # validate an attributes as a SAT Public Name, maybe
                # reflect the validation in the vector, return the valid
                # name and its horizon.
                #
                horizon = set ()
                chunks = []
                pns_sat.pns_sat_articulate (encoded, horizon, chunks)
                if len (chunks) > 1 and len (horizon) < 126:
                        horizon = set ()
                        valid = pns_model.pns_name (netstrings_encode (
                                [name for name, text in chunks]
                                ), horizon)
                elif len (chunks) > 0:
                        valid = chunks[0][0]
                else:
                        valid = ''
                return (valid, horizon)
                
        def presto_pns_statement (self, reactor):
                # statements
                context, context_horizon = self.presto_pns_validate (
                        reactor.presto_vector[u'context'].encode ('UTF-8')
                        )
                subject, context_horizon = self.presto_pns_validate (
                        reactor.presto_vector[u'subject'].encode ('UTF-8'), 
                        context
                        )
                if subject == '':
                        return
                        
                predicate = reactor.presto_vector[u'predicate'].encode ('UTF-8')
                predicates = netstrings_decode (predicate)
                obj = reactor.presto_vector[u'object'].encode ('UTF-8')
                if obj == '' and len (predicates) > 1:
                        react = PRESTo_subject ()
                        pns_articulator.PNS_articulate_subject (
                                self, subject, predicates
                                ).finalization = react
                        return react
                                
                react = PRESTo_statement ()
                self.pns_statement (
                        (subject, predicate, obj), context, react
                        )
                return react
                
        def presto_pns_protocol (self, reactor):
                # articulate a protocol statement
                #
                subject, subject_horizon = self.presto_pns_validate (
                        reactor.presto_vector[u'subject'].encode ('UTF-8')
                        )
                if subject == '':
                        return
                        
                obj = reactor.presto_vector[u'object'].encode ('UTF-8')
                react = PRESTo_reactor (
                        self.pns_articulate_protocol_continue
                        )
                self.pns_client.pns_statement (
                        (subject, '', obj), subject, react
                        )
                return react
                
        def presto_pns_command (self, reactor):
                predicate, predicate_horizon  = self.presto_pns_validate (
                        reactor.presto_vector[u'predicate'].encode ('UTF-8')
                        )
                obj, predicate_obj = self.presto_pns_validate (
                        reactor.presto_vector[u'object'].encode ('UTF-8')
                        )
                if predicate == obj == '':
                        return
                        
                triple = ('', predicate, obj)
                if self.pns_commands.has_key (triple):
                        self.pns_articulate_command_continue (
                                triple, self.pns_commands[triple]
                                )
                        return
                        
                react = PRESTo_command ()
                self.pns_command (triple, react)
                return react

        def presto_pns_protocol_continue (self, resolved, model):
                return False
                        
                        
presto_components = (PRESTo_articulator, )