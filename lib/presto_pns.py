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
        pns_model, pns_xml, pns_client, pns_articulator,
        presto, presto_http
        )


# PRESTo/PNS Component Object Model

class PRESTo_dom (
        pns_xml.PNS_XML, loginfo.Loginfo, finalization.Finalization
        ):
        
        "PNS/XML implementation of PRESTo's COM interfaces"
        
        def __init__ (self, name, types={}, type=presto.PRESTo_async):
                self.xml_prefixes = {u'http://presto/': u'presto'}
                self.xml_pi = {}
                self.xml_type = type
                self.xml_types = types
                self.presto_name = name
                        
        def __repr__ (self):
                return 'presto-pns-dom name="%s"' % self.presto_name
        
        xml_name = 'http://presto/ pns'

        presto_defered = None
        
        # The PRESTo commit and rollback interfaces
        
        def presto_rollback (self, defered): 
                # yes I use defered too (but just a list is enough to 
                # implement them, thank you ;-)
                try:
                        self.presto_defered.append (defered)
                except:
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
                
                self.xml_to_pns (
                        self.presto_name, 
                        self.presto_root.presto_host,
                        self.pns_client.pns_statement
                        )
                defered[0] (*defered[1]) 
                return True
                #
                # no actual defered on commit, waiting for the peer's
                # acknowledgement has no purpose unless you expect to 
                # rollback immediately after a commit.
        
        def pns_to_xml_continue (self, finalized):
                "PNS/XML rolledback"
                e = finalized.xml_parsed
                if e and e.xml_valid != None:
                        e.xml_valid (self)
                self.xml_root = e
                defered = self.presto_defered
                self.presto_defered = self.pns_statement = None
                for callback, args in defered:
                        callback (*args)
                

# PNS/REST client component and methods

class PNS_statement (producer.Stalled_generator):
        
        def __init__ (self, prefixes, encoding='ASCII'):
                self.xml_prefixes = prefixes
                self.encoding = encoding
        
        def __call__ (self, resolved, model):
                if not model[3] and model[2]:
                        self.generator = pns_xml.statements_unicode (
                                model, self.xml_prefixes, self.encoding
                                )
                else:
                        self.generator = pns_xml.statement_unicode (
                                model, self.xml_prefixes, self.encoding
                                )
                return False

        # a fine example of a Stalled_generator application, producing
        # the prefixed and encoded XML string for any PNS response, but
        # stalling the HTTP response producer until the question is resolved 
        # by a PNS/TCP client or an articulator.
        #
        # note how the same instance holds state for the stalled HTTP 
        # response *and* serves as a handler for the PNS/TCP question.
                
                
def pns_graph_rest (ci):
        context, index = netstring.decode (ci)
        return ''.join ((
                '<pns:graph>',
                pns_xml.name_unicode (context, 'pns:context'),
                pns_xml.name_unicode (index, 'pns:index'),
                '</pns:graph>'
                ))


class PNS_command (producer.Stalled_generator):
        
        def __call__ (self, resolved, model):
                if resolved[1] == '':
                        self.generator = iter ((
                                pns_xml.name_unicode (
                                        model[3], 'pns:index'
                                        ),
                                ))
                elif resolved[2] == '':
                        self.generator = (
                                pns_xml.name_unicode (
                                        context, 'pns:context'
                                        ) 
                                for context in netstring.decode (
                                        model[3]
                                        )
                                )
                elif model[3]:
                        self.generator = (
                                pns_graph_rest (ci)
                                for ci in netstring.decode (model[3])
                                )
                else:
                        self.generator = iter (('<pns:graph/>',))
                return False
                        

def pns_open (component, reactor):
        metabase = component.xml_attributes.setdefault (
                u'metabase', u'127.0.0.1:3534'
                ).encode ('ASCII', 'ignore')
        try:
                host, port = metabase.split (':')
        except:
                channel = component.PNS_CLIENT (
                        (metabase, 3534), component.pns_peer
                        )
        else:
                channel = component.PNS_CLIENT (
                        (host, int (port)), component.pns_peer
                        )
        if channel:
                component.pns_client = channel
                component.xml_dom = reactor.presto_dom
                return True
        
        return False


def pns_peer (component, resolved, model):
        ip = model[3]
        if ip:
                component.xml_attributes[u'peer'] = unicode (ip, 'UTF-8')
                return True # opened, keep this handler
                
        component.pns_client = None
        try:
                del component.xml_attributes[u'peer']
        except KeyError:
                pass
        component.xml_dom = None # de-cycle on close, unload from cache!
        return False # closed, release this handler


def pns_statement (component, reactor):
        "pass-through method for PNS/TCP statements"
        if not reactor.presto_vector:
                return '<pns:statement/>'
        
        if component.pns_client == None and not pns_open (
                component, reactor
                ):
                return '<pns:tcp-error/>'
                
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
                                return '<pns:statement/>'
                        
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
        
        
class PNS_TCP (presto.PRESTo_async):
        
        xml_name = u'http://pns/ tcp'
        
        PNS_CLIENT = pns_client.PNS_client ()

        pns_client = None

        def __init__ (self, name, attr):
                self.xml_attributes = attr or {}

        def xml_valid (self, dom):
                dom.xml_prefixes['http://pns/'] = 'pns'
        
        pns_peer = pns_peer

        def pns_log (self, model):
                pass # TODO: move to a BSDDB queue ...                

        presto = presto_http.get_rest
                        
        presto_interfaces = set ((
                u'subject', u'predicate', u'object', u'context', 
                ))

        presto_methods = {None: pns_statement}
