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
# This is a set of PNS/TCP user agent components for PRESTo.
#
# The PNS/TCP client is implemented as a folder component. Deployed
# as the instance:
#
#        http://hostname/pns
#
# it provides a usefull "pass-through" REST interface for PNS/TCP
# 3-bit syntax for stateless HTTP clients:
#
#        ?subject=&predicate=&object=&context=
#
# holds the state of a session:
#
#        <allegra:pns
#                tcp-ip="127.0.0.1"
#                tcp-port="3534"
#                udp-ip="w.x.y.z"
#                >
#                <allegra:context>
#                <allegra:context 
#                        name="6:Public,5:Names,"
#                        left="w.x.y.z" 
#                        right="w.x.y.z"
#                        />
#        </pns-tcp>
#
# and manages a folder interface for PNS/SAT, PNS/MIME or PNS/XML 
# articulators
#
#        ~/context
#
# for:
#
#        ~/context?articulate=simple_articulated_text
#
# maintaining allways at least one open articulator ready.
#
#        ~/
#
#        <?xml-stylesheet type="text/xsl" href="/styles/pns_xml.xsl"?>
#        <allegra:pns-xml
#                lang="en"
#                context=""
#                predicates="3:xml,"
#                />
#
# Allegra test case consists in an English SAT articulator for RSS/XML:
#
#        ~/6:Planet,6:Python,
#
#        <?xml-stylesheet type="text/xsl" href="/styles/pns_rss.xsl"?>
#        <allegra:pns-xml
#                lang="en"
#                context="6:Planet,6:Python,"
#                predicates="7:channel,4:item,"
#                />
#
#        ?subject=&predicate=&object
#
# that returns a PNS/XML response:
#
#         ...
#
# and updates the PRESTo instance element tree with a cached RSS/XML string
# made of all subjects eventually articulated:
#
#        ~/6:Planet,6:Python,/Zope?predicate=&object=
#
#
# and a MIME articulator with French SAT support:
#
#        ...
#
# The objective of presto_pns.py is to provide a practical way to mix in
# a web distinct instances of different classes derived from the articulator
# component. Practically The Semantic Web Peer must integrate a PNS/XML
# articulator with english PNS/SAT parameters and RSS attributes and style
# for a context like "planet.perl.org", but also use a french SAT with a 
# MIME articulator for a context like "fr.lang.python".
#
#        http://hostname/pns/2:fr,4:lang,6:python,
#
#        <?xml-stylesheet type="text/xsl" href="/styles/pns_usenet.xsl"?>
#        <allegra:pns-mime
#                lang="fr"
#                context="2:fr,4:lang,6:python,"
#                predicates="4:body,4:date,4:from,7:subject,"
#                />
#
#        ?subject=&predicate=&object
#
#
# Allegra PRESTo!
#
# Eventually, a PNS metabase is a good tool to manage that web, and 
# PRESTo PNS folder uses its PNS/TCP connextion to commit and rollback
# any component instances as a PNS/XML articulation.
#
# Allegra provides a simple asynchronous API to articulate an XML element
# tree to and from a PNS metabase. To retrieve an sequence of XML documents
# associated to a subject:
#
#        PRESTo_pns_articulate_xml (
#                'subject', 
#                ('<?xml version="1.0" "encoding="UTF-8"?>', )
#                ).finalization = ...
#
# to get an sequence of element trees, do:
#
#        PRESTo_pns_articulate_xml (
#                'subject', ('title', 'pubDate', 'description', )
#                ).finalization = ...
#
#
# Asynchronous cache are good. They are fast. And on a network peer, 
# they are resilient. You simply can't scale up an SOA without facing
# the "riddle of asynchrony".
#
#
# Blurb Mode
#
# Blurb about the whole web stack and how PNS "slips under" to fix
# what is broken for better public applications of the network, and
# how good Allegra reimplements that stack to actually serve such
# service on a grid of peers. Asynchronously. Fast. Reliable.
#
# HTTP is stateless. To scale up, either you add a forward cache in your 
# SOA or you cache at each peer of that network architecture. That's what 
# Allegra does. To build a large metabase for large network applications, 
# with high reliability and high performances, Allegra's web peer
# caches as much of its users articulation as possible. There is no need
# for a network made of ever more complex layers of web indirection, static
# and forward caches, to speed up rather heavy LAMP backends tied to some 
# synchronized SQL server instance.
#
# Semantic Web Service
#
# Allegra PRESTo, completed, will be a PNS/HTTP/RSS/MIME user agent that read
# news and mail from any browser, fast. At home on an old PC or a new Mac. 
# At work on cheap individual network disks or expensive PDA. Or both. Also 
# on the Internet, somewhere on a blade, preferrably in a datacenter. And 
# maybe, why not, in your phone? With a simple protocol for something better
# than replication: peer review.
#
# If there is 4GB of memory to hold state and a 3.4Ghz processor to drive 
# the computer system, its Gigabit connection will be the bottleneck for
# an asynchronous peer. A "scripted" host like Allegra is not a high
# performance system, but it supports high performance applications.
#
# Since people pay for productive applications, not fast system, an
# apparently too simple and inherently slow way to do it wins the game
# if it can effectively used to develop better applications instead of 
# faster systems.
#
# Peer Network
#
# The simple truth is that any small and simple enough peer darwfs a 
# giant server ... on an IP network.
#
# Even a simple phone can do better than a monstruous SOA running on
# expensive servers and very expensive storage systems. The Internet is
# a public network of peers, built like that from ground up, and nobody
# is going to change that soon. There are 300 millions registered DNS
# domain names, probably several times more than the number of concurrent 
# IP addresses in use on the Internet. Looking as one ratio, all web servers 
# are just centralized peers.
#
# The Internet is a peer network. HTTP is somehow built for a peer network
# and DNS domains manage to somehow distribute it. Neither HTTP nor DNS are
# eternal as the primary vectors of the web. Piggy backs peer networks have 
# developped on the web protocol (Gnutella, BitTorrent, RSS, ...) or as
# web services because there are very usefull applications of the Internet
# *as a network of peers*.
#
# A Public Name System
#
# PNS etc ...
#
