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

from allegra import \
        netstring, finalization, reactor, \
        pns_model, pns_sat, pns_xml, pns_client, pns_articulator, \
        presto


class PRESTo_pns_statement (reactor.Buffer_reactor):
        
        def __call__ (self, resolved, model):
                self.buffer (pns_xml.pns_xml_unicode (
                        model, pns_xml.pns_cdata_unicode (model[2])
                        ))
                self.buffer ('')
                return False
                        
                        
class PRESTo_pns_command (reactor.Buffer_reactor):
        
        def __call__ (self, resolved, model):
                if resolved[1] == '':
                        if model:
                                self.buffer (pns_xml.pns_names_unicode (
                                        model[0], tag='allegra:index', attr=''
                                        ))
                        else:
                                self.buffer ('<allegra:index name=""/>')
                elif resolved[2] == '':
                        if model:
                                self.buffer (''.join ([
                                        pns_xml.pns_names_unicode (
                                                context, tag='allegra:context', 
                                                attr='' 
                                                ) 
                                        for context in model[1]
                                        ]))
                        else:
                                self.buffer ('<allegra:context name=""/>')
                else:
                        self.buffer ('<allegra:routes/>')
                self.buffer ('')
                return False
                        
                        
# TODO: move to pns_xml ?
                                
class PNS_articulate_xml (finalization.Finalization):
        
        # aggregate an XML strings for a given subject, attach the result
        # tree or CDATA to the given parent, then finalize.

        def __init__ (self, articulator, subject, predicates, parent):
                self.xml_parent = parent
                self.pns_articulator = articulator
                self.pns_subject = subject
                self.pns_predicates = predicates
                # first ask for all contexts for this subject ...
                self.pns_articulator.pns_command (
                        ('', subject, ''), self.pns_resolve_contexts
                        )

        def pns_resolve_contexts (self, resolved, model):
                if model == None:
                        return # ... no contexts, stop.
                        
                # reference the context set and ask for all predicates
                # in any context ...
                #
                self.pns_contexts = model[1]
                for predicate in predicates:
                        self.pns_articulator.pns_statement (
                                (resolved[1], predicate, ''), 
                                '', self.pns_resolve_predicate
                                )

        def pns_resolve_predicate (self, resolved, model):
                if model[2]:
                        if model[3]:
                                # single contextual answer
                                self.pns_articulate_xml (model[2], model[3])
                        else:
                                # multiple contextual answers
                                for co in netstring.decode (model[2]):
                                        c, o = netstring.decode (co)
                                        self.pns_articulate_xml (o, c)
        
        def pns_articulate_xml (self, obj, context):
                # validate the object as XML, parse as an element tree ...
                #
                dom = XML_dom ()
                dom.xml_unicoding = 0
                dom.xml_parser_reset ()
                e = dom.xml_parse_string (obj)
                if e == None:
                        return # ... parser error, drop object and context.
                        
                # append a valid element to the tree and set its context
                # attribute ...
                #
                if e.xml_attributes == None:
                        e.xml_attributes = {'context': context}
                else:
                        e.xml_attributes['context'] = context
                self.xml_parent.xml_children.append (e)
                if not e.xml_children:
                        return # ... stop if it has no child
                        
                # find out the tags to articulate, only for attribute-less
                # empty elements. the purpose is to allow applications to
                # pack a minimal XML tree in one PNS statement and retrieve 
                # it at once. Or, as it is often the case with multi-parts
                # documents, as one "envelope" and distinct "parts" ...
                #
                predicates = set ([
                        xml_tag (child.xml_name)
                        for child in e.xml_children
                        if not (
                                child.xml_attributes or
                                child.xml_first or 
                                child.xml_children
                                )
                        ]).difference (self.pns_predicates)
                if len (predicates) == 0:
                        return # ... no predicates, stop.
                        
                # clear the children list from the articulated elements
                e.xml_children = [
                        child for child in e.xml_children
                        if (
                                child.xml_attributes or
                                child.xml_first or 
                                child.xml_children or
                                xml_tag (child.xml_name) in predicates
                                )
                        ]
                # then continue to articulate ...
                PNS_articulate_xml (
                        self.pns_articulator, self.pns_subject, predicates, e
                        ).finalization = self
                                
        def __call__ (self, finalized):
                pass # ... and finally join ;-)


class PRESTo_pns_articulate (reactor.Buffer_reactor):
        
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
                                

class PRESTo_pns_articulator (
        presto.PRESTo_async, pns_articulator.PNS_articulator
        ):
                 
        presto_interfaces = set ((u'articulated', u'predicates'))
                
        xml_name = u'http://allegra/ articulator'

        pns_client = None
        
        def xml_valid (self, dom):
                self.xml_dom = dom

        def presto (self, reactor):
                # articulate an XML string
                if self.pns_client == None:
                        return self.presto_pns_open (reactor)

                articulated, horizon = self.sat_articulate (
                        reactor.presto_vector[u'articulated'].encode ('UTF-8')
                        )
                if not articulated:
                        return

                react = PRESTo_articulate ()
                pns_articulator.PNS_articulate (
                        self, articulated, netstring.netlist (
                                reactor.presto_vector[
                                        u'predicates'
                                        ].encode ('UTF-8') or 'sat'
                                )
                        ).finalization = react
                return react
                
        def pns_multiplex (self, model):
                pass

        def sat_articulate (self, encoded, context=''):
                # articulate as a SAT Public Name return the valid name and 
                # its horizon.
                #
                horizon = set ()
                chunks = []
                pns_sat.pns_sat_articulate (encoded, horizon, chunks)
                if len (chunks) > 1 and len (horizon) < 126:
                        horizon = set ()
                        valid = pns_model.pns_name (netstring.encode (
                                [name for name, text in chunks]
                                ), horizon)
                elif len (chunks) > 0:
                        valid = chunks[0][0]
                else:
                        valid = ''
                return (valid, horizon)
                
        presto_methods = {}
                

class PRESTo_pns (presto.PRESTo_async):
        
        # A client component, but also a PRESTo root, a truly multi purpose
        # class that aggregates several interfaces and makes a complex
        # architecture as simple as possible.
        #
        # Here is how it works:
        #
        # This class can be "pulled" into PRESTo's instance cache by the
        # client, or "loaded" first by the server. It's weak reference in
        # the cache will then not be released until it is itself deleted
        # from the list of PRESTo roots.
        
        xml_name = u'http://allegra/ pns'
        
        pns_client = None

        def xml_valid (self, dom):
                self.xml_dom = dom
                self.pns_articulator = {
                        '': PRESTo_pns_articulator ()
                        }

        def presto_folder (self, base, path):
                articulator = self.pns_articulators.get (path)
                if articulator != None:
                        return articulator
                        
                context = pns_name (path, set ())
                if context != path:
                        return
                        
                articulator = PRESTo_pns_articulator ()
                articulator.xml_attributes[u'context'] = context
                self.pns_articulators[context] = articulator
                return articulator
                
        presto_interfaces = set ((
                u'subject', u'predicate', u'object', u'context'
                ))
                        
        def presto (self, reactor):
                if self.pns_client == None:
                        return self.pns_open (reactor)

                model = (
                        reactor.presto_vector[u'subject'].encode ('UTF-8'),
                        reactor.presto_vector[u'predicate'].encode ('UTF-8'),
                        reactor.presto_vector[u'object'].encode ('UTF-8')
                        )
                context = reactor.presto_vector[u'context'].encode ('UTF-8')
                if '' == model[0]:
                        if '' == model[1] == model[2]:
                                self.pns_client.pns_quit (
                                        context, self.pns_articulators[context]
                                        )
                        else:
                                react = PRESTo_pns_command ()
                                self.pns_command (model, react)
                                return react
                                
                elif '' == model[1] and model[0] == context:
                        if model[2]:
                                self.pns_client.pns_join (
                                        context, model[2],
                                        self.pns_articulators[context],
                                        )
                        else:
                                self.pns_client.pns_subscribe (
                                        context, self.pns_articulators[context]
                                        )
                else:
                        react = PRESTo_pns_statement ()
                        self.pns_client.pns_statement (model, context, react)
                        return react

        def pns_open (self, reactor):
                if self.pns_client != None:
                        return '<allegra:pns-tcp-open/>'
                        
                self.pns_client = pns_client.PNS_client_channel ()
                if self.pns_client.tcp_connect ((
                        self.xml_attributes.get (u'tcp-ip', '127.0.0.1'),
                        int (self.xml_attributes.get (u'tcp-port', '3534'))
                        )):
                        self.pns_client.pns_peer = react = PRESTo_reactor (
                                self.pns_peer, '<allegra:pns-tcp-open/>'
                                )
                        return react
                        
                self.pns_client = None
                return '<allegra:pns-tcp-connection-error/>'
                
        def pns_close (self, reactor):
                if self.pns_client == None:
                        return '<allegra:pns-tcp-close/>'
                        
                # close the PNS/TCP session, finalize the client
                self.pns_client.pns_peer = react = \
                         PRESTo_reactor (
                                 self.pns_peer, '<allegra:pns-tcp-close/>'
                                 )
                self.pns_client.push ('12:0:,0:,0:,0:,,')
                self.pns_client.close_when_done ()
                return react
                        
        def pns_peer (self, ip):
                if ip:
                        # opened
                        self.xml_attributes[
                                u'udp-ip'
                                ] = unicode (ip, 'UTF-8')
                        self.pns_client.pns_peer = self.pns_peer 
                        return
                        
                # closed
                del self.pns_client.pns_peer
                self.pns_client = None
                try:
                        del self.xml_attributes[u'udp-ip']
                except KeyError:
                        pass
                self.xml_dom = None # clear on close!


# Note about this implementation
#
# A <presto:pns/> instance is at the same time a folder and a root, 
# accessible from another instance cache than its own, usually in
# the loopback namespace with the virtual host name it serves:
#
#        http://127.0.0.1/allegra
#
# beeing the root of:
#
#        http://allegra/
#
# For each <presto:pns/> instanciated, a PNS/TCP session is established
# to the ip address and port found in its XML attributes, which then
# subscribes to a context named as the virtual host served:
#
#        7:allegra,0:,0:,7:allegra,
#
# and to any context found in the response to:
#
#        7:allegra,0:,0:,0:,
#
# For each context subscribed an articulator is loaded from PNS in the cache, 
# if there is an answer for:
#
#        7:context,7:articulate,0:,7:allegra,
#
# otherwise the PNS metabase is updated with:
#
#        <presto:articulate context="context"/>
#
# whatever it is. In any case, an instance is available before three seconds
# which will be updated when dissent comes to the network.
#
# Practically, each virtual host represents an application context and a
# distinct PNS/TCP session, each contexts subscribed is a distinct channel
# of communication with its own metabase cache ... and folder interface.
#
# This makes sense for a single peer as well as for a distributed service,
# but with a different interpretation of the names found in a URL:
#
#        http://application.user/context/subject
#
# for a peer with a single user but many applications and
#
#        http://user.application/context/subject
#
# for a multi-user service that can be integrated into the existing SSL/TLS
# authentification protocols (it is that simple, go figure why?).
#
# Now, back to earth. For a single peer application developper with pies in
# their skies, this is a very practical way to solve the scale problem they
# may face if their application is successfull. Up front, instances are made
# persistent in a distributed metabase and the practical effect of a user
# session obtained by subscribing to the application's context. So that
# scaling is simple as piling up boxes and distributing users on loose
# fitting peers: "one size fits all", PRESTo! Each application should be
# implemented by "seed" PNS user agents that doe hold a context as long
# as possible and simply logs, then provided with a set of roots and 
# articulator components derived from these. Then as functions emerge from
# data collection, an application can be developped as XSLT style sheets
# or JavaScript articulations of the PNS articulator interfaces (command,
# protocol and statement). 
#
# The ones provided are:
#
#        articulate (name)
#        get (subject, predicate)
#        edit (subject, predicate, object)
#        tag (subject, predicate, object, context)
#
# integrated in one XSLT style sheet for each articulators of Allegra
# application test case (MIME, RSS and HTML). It is possible to develop
# a complete PRESTo/PNS application without writing one line of Python
# (otherwise it is not a good framework, see the success of plone ;-).
# AJAX clients may do a lot more with those four to provide users with an 
# interactive ans snappy content management interface.
#
# Most remarkably, this architecture makes the PNS/TCP interface available
# REST interfaces in two distinct namespaces, a PNS articulator interface 
# implemented differently for each context, and a simpler pass-through 
# PNS/TCP interface preferrably in a restricted namespace binded to a
# private network interface.
#
# Practically, this rather complex architectural statement means that 
# PRESTo/PNS applications come "ready-made" with both public and private 
# interfaces to manage them. The private pass-through interface for the 
# application's managers and the public articulated interface for the 
# application's users. Instances are created through the private
# interfaces by the site managers, while articulators validate context and
# subject before subscribing or stating to the metabase.
#
# This architecture yields a practical way to manage a distributed metabase
# application, where each peer hosts many users, where users and metabases
# are managed but not subject and contexts, which are distributed by each 
# metabase as its users shape it.
#
# Semantically translated in the context of a single user peer and multiple 
# applications, it also means that the PRESTo/PNS applications can provide
# the same metabase management interface for REST user agents. For instance,
# the application manager can "open" the metabase through the web and create
# new component instances in the application's namespace from a simple
# or more articulated console (Or it may be done by the host system itself,
# possibly by the browser too when PRESTo runs along Mozilla ;-)
#
#