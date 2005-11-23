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

# TODO: move back to the library, in presto_pns.py as base components
#       for PNS articulators that share one multiplexer. this is the
#       default, one PNS/TCP client per PRESTo root.
#
#       the articulator components are contained by the client
#       component (pns.xml) which manages caches entries for it
#       in the PRESTo root, using the folder interface.
#

from allegra.xml_dom import XML_element
from allegra.xml_unicode import xml_cdata, xml_attr
from allegra.presto import \
        PRESTo_async, PRESTo_reactor, presto_xml, \
        PRESTo_sync, presto_synchronize

from allegra import \
        netstring, pns_model, pns_sat, pns_xml, pns_client, pns_articulator


class PNS_presto_log (XML_element):
                
        xml_name = 'http://allegra/ pns-log'
        
        def xml_valid (self, dom):
                self.xml_children = []
        
        def __call__ (self, model):
                self.xml_children.insert (0, pns_xml.pns_xml_unicode (
                        model, '<![CDATA[%s]]>' % model[2]
                        ))


class PNS_presto_articulator (
        XML_element, pns_articulator.PNS_articulator
        ):
                 
        presto_interfaces = set ((
                u'PRESTo', 
                u'articulated', 
                u'subject', u'predicate', u'object', u'context'
                ))
                
        xml_name = u'http://allegra/ pns-articulator'
        
        def xml_valid (self, dom):
                self.xml_children = [
                        '<pns:index/>',
                        '<pns:contexts/>',
                        '<pns:objects>',
                        '</pns:objects>',
                        ]

        def pns_presto_articulate (self, reactor):
                articulated, horizon = self.pns_validate (
                        reactor.presto_vector[u'articulated'].encode ('UTF-8')
                        )
                if not articulated:
                        return

                names = netstring.netstrings (articulated)
                if len (names) > 1:
                        # articulate a search ...
                        react = PRESTo_reactor (
                                self.pns_articulate_routes_continue
                                )
                        route = pns_articulator.PNS_walk_routes ()
                        pns_articulator.PNS_walk_articulated (
                                self, articulated, names
                                ).finalization = route
                        route.finalization = react
                        return react
                        
                # just get the index and let the user walk ...
                react = PRESTo_reactor (self.pns_articulate_command_continue)
                self.pns_command (('', '', articulated), react)
                return react

        def pns_presto_statement (self, reactor):
                if self.pns_client == None:
                        return # not connected!
                
                if reactor.presto_vector[u'subject']:
                        if (
                                reactor.presto_vector[u'context'] or 
                                reactor.presto_vector[u'predicate'] 
                                ):
                                return self.pns_articulate_statement (reactor)

                        return self.pns_articulate_protocol (reactor)
                        
                # commands
                return self.pns_articulate_command (reactor)
                
        presto_methods = {
                u'articulate': pns_presto_articulate, 
                u'pns': pns_presto_statement, 
                }
        
        def pns_validate (self, encoded, context=''):
                # validate an attributes as a SAT Public Name, maybe
                # reflect the validation in the vector, make a SAT statement
                # and return its reactor.
                #
                horizon = set ()
                valid = pns_sat.pns_sat_and_re (encoded, horizon)
                return (valid, horizon)
                
        def pns_articulate_statement (self, reactor):
                # statements
                context, context_horizon = self.pns_validate (
                        reactor.presto_vector[u'context'].encode ('UTF-8')
                        )
                subject, subject_horizon = self.pns_validate (
                        reactor.presto_vector[u'subject'].encode ('UTF-8')
                        )
                if subject == '':
                        return
                        
                predicate = reactor.presto_vector[u'predicate'].encode ('UTF-8')
                predicates = netstring.netstrings (predicate)
                obj = reactor.presto_vector[u'object'].encode ('UTF-8')
                if obj == '' and len (predicates) > 1:
                        react = PRESTo_reactor (
                                self.pns_articulate_objects_continue
                                )
                        pns_articulator.PNS_walk_objects (
                                self, subject, predicates
                                ).finalization = react
                        return react
                                
                react = PRESTo_reactor (
                        self.pns_articulate_object_continue
                        )
                self.pns_statement (
                        (subject, predicate, obj), context, react
                        )
                return react
                
        def pns_articulate_protocol (self, reactor):
                # articulate a protocol statement
                #
                subject, subject_horizon = self.pns_validate (
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
                
        def pns_articulate_command (self, reactor):
                predicate, predicate_horizon  = self.pns_validate (
                        reactor.presto_vector[u'predicate'].encode ('UTF-8')
                        )
                obj, predicate_obj = self.pns_validate (
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
                        
                react = PRESTo_reactor (self.pns_articulate_command_continue)
                self.pns_command (triple, react)
                return react
                
        def pns_articulate_objects_continue (self, finalized):
                for model in finalized.pns_objects:
                        self.xml_children.insert (
                                3, pns_xml.pns_xml_unicode (
                                        model, 
                                        pns_xml.pns_cdata_unicode (model[2])
                                        )
                                ) # let the XSL stylesheet display!
                del finalized.pns_articulator
                
        def pns_articulate_routes_continue (self, finalized):
                if len (finalized.pns_routes) > 0:
                        self.xml_children[1] = ''.join ([
                                pns_xml.pns_names_unicode (
                                        context, tag='pns:context', attr='' 
                                        )
                                for context, index in finalized.pns_routes
                                ])
                del finalized.pns_articulator
                
        def pns_articulate_command_continue (self, resolved, model):
                if resolved[1] == '':
                        if not model[1]:
                                return False
                                
                        self.xml_children[0] = pns_xml.pns_names_unicode (
                                model[0], tag='pns:index', attr=''
                                )
                elif resolved[2] == '':
                        self.xml_children[1] = ''.join ([
                                pns_xml.pns_names_unicode (
                                        context, tag='pns:context', attr='' 
                                        ) for context in model[1]])
                else:
                        pass
                        # self.xml_children[2] = pns_xml.pns_routes_unicode (
                        #        model
                        #        )
                return False
                        
        def pns_articulate_statement_continue (self, resolved, model):
                return False
                        
        def pns_articulate_protocol_continue (self, resolved, model):
                return False
                        
                        
# TODO: delete this component altogether, merge its function with the
#       articulator?

class PNS_presto_console (PRESTo_async):

        xml_name = u'http://allegra/ pns-session'

        # PRESTo interfaces
                
        def xml_valid (self, dom):
                # Binds the root element instance to its DOM, making any
                # weakref for the DOM "hold" as long as the implied circular
                # reference does.
                #
                # (or how to turn a common bug in a usefull function ;-)
                #
                self.xml_dom = dom
                #self.pns_log = PNS_presto_log ()
                #self.pns_log.xml_valid (dom)
                self.pns_articulator = PNS_presto_articulator ()
                self.pns_articulator.xml_valid (dom)
                self.xml_children = [
                        self.pns_articulator #, self.pns_log
                        ]
         
        presto_interfaces = set ((
                u'PRESTo', 
                u'articulated',
                u'subject', u'predicate', u'object', u'context'
                ))
                
        pns_client = None

        def pns_open (self, reactor):
                if self.pns_client == None:
                        self.pns_client = pns_client.PNS_client_channel ()
                        if self.pns_client.tcp_connect ():
                                # self.pns_client.pns_log = self.pns_log
                                self.pns_client.pns_peer = react = \
                                         PRESTo_reactor (self.pns_peer)
                                return react
                                
                        self.pns_client = None

        def pns_close (self, reactor):
                if self.pns_client != None:
                        # close the PNS/TCP session, finalize the client
                        self.pns_client.push ('12:0:,0:,0:,0:,,')
                        self.pns_client.close_when_done ()
                        self.pns_closed ()
                        self.xml_dom = None # clear on close!

        def pns_presto_articulate (self, reactor):
                if self.pns_client == None:
                        return # not connected!
                
                return self.pns_articulator.pns_presto_articulate (reactor)
                        
        def pns_presto_statement (self, reactor):
                if self.pns_client == None:
                        return # not connected!
                
                return self.pns_articulator.pns_presto_statement (reactor)
                        
        presto_methods = {
                u'open': pns_open,
                u'close': pns_close,
                u'articulate': pns_presto_articulate,
                u'pns': pns_presto_statement,
                }
        
        presto = pns_presto_articulate
        
        # implementation

        def pns_peer (self, peer):
                # react to the PNS events open or close.
                if peer:
                        self.xml_attributes[
                                u'pns-udp-ip'
                                ] = unicode (peer, 'UTF-8')
                        self.pns_articulator.pns_client = self.pns_client
                        self.pns_client.pns_peer = self.pns_closed 
                else:
                        self.pns_articulator.pns_client = \
                                self.pns_client = None
                                        
        def pns_closed (self, ip=''):
                # called-back when the PNS/TCP client channel is closed
                #del self.pns_client.pns_log
                del self.pns_client.pns_peer
                self.pns_client = None
                try:
                        del self.xml_attributes[u'pns-udp-ip']
                except KeyError:
                        pass


presto_components = (
        PNS_presto_console, 
        PNS_presto_articulator, 
        )
        

if __debug__:
        from allegra import presto_prompt 
        presto_prompt.presto_debug_async (PNS_presto_articulator)
        presto_prompt.presto_debug_sync (PNS_presto_console)


def presto_reload ():
        # allow to debug those too without reloading individually,
        # as this module itself is reloaded.
        #
        for module in (
                pns_model, pns_sat, pns_xml, pns_client #, pns_search
                ):
                reload (module)
                
                
# Note about this implementation
#
# The pns.py module provides two components that implements a test case
# for both Allegra's PNS peer and PRESTo web peer.
#
# PNS_agent manages a PNS/TCP user agent that logs to BSDDB table(s) and
# provides web users with the following methods:
# 
# 0. ?PRESTo=articulate&subject=
#
#    This is the "Start" of Allegra, its main interface. For each new
#    subject articulated, the agent step once the semantic graph in both
#    directions and returns the mapped contexts and indexed names, as
#    well as any Public RDF statements for the given predicates (defined
#    for the component instance).
#
#    If the subject articulated is an HTTP URI, the resource described
#    is retrieved and indexed if it's guessed mime type is either HTML
#    or XML. A few namespaces are partially supported, including RSS.
#
# 1. ?PRESTo=edit&subject=&predicate=&object=&context=
#
#    Edit a Public RDF statement, new or old.
#
# 2. ?PRESTo=subscribe&subject= and ?PRESTo=unsubscribe&subject=
#
#    Subscribe/unsubscribe to a context
#

# A transient web SAT console for PNS/TCP:
#
# <?xml version="1.0" encoding="UTF-8"?>
# <allegra:console
#     pns-tcp-ip="127.0.0.1:3534"
#     pns-udp-ip=""
#     xmlns:pns="http://pns/"
#     xmlns:presto="http://presto/"
#     xmlns:allegra="http://allegra/"
#     >
#     <allegra:contexts/>
#     <allegra:articulator
#         sat-whitespace=" "
#         sat-strip=" "
#         sat-brackets="()[]{}<>"
#         sat-punctuation=".?!,:;&quot;|=+-/"
#         >
#         <pns:statement/>
#     </allegra:articulator>
#     <allegra:log>
#         <pns:statement/>
#     </allegra:log>
# </allegra:console>
#
#
