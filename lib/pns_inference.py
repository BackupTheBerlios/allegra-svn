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

import glob, bsddb

from allegra import netstring, thread_loop, netunicode, public_names


NULL_SET = frozenset ()

class PNS_inference (thread_loop.Thread_loop):
        
        pns_horizon = 126

        def __init__ (self, pns_peer):
		self.pns_peer = pns_peer
                self.pns_root = pns_peer.pns_root
		thread_loop.Thread_loop.__init__ (self)
                self.start ()

	def __repr__ (self):
		return 'pns_inference'

	def thread_loop_init (self):
		try:
			self.pns_routes = bsddb.db.DB ()
                        if glob.glob (self.pns_root + '/contexts.db'):
                                self.pns_routes.open (
                                        self.pns_root + '/contexts.db'
                                        )
                        else:
                                self.pns_routes.open (
				        self.pns_root + '/contexts.db',
                                        dbtype=bsddb.db.DB_HASH,
                                        flags=bsddb.db.DB_CREATE
				        )
			self.pns_index = bsddb.db.DB ()
                        if glob.glob (self.pns_root + '/names.db'):
                                self.pns_index.open (
                                        self.pns_root + '/names.db'
                                        )
                        else:
                                self.pns_index.open (
				        self.pns_root + '/names.db',
                                        dbtype=bsddb.db.DB_HASH,
                                        flags=bsddb.db.DB_CREATE
				        )
		except:
                        self.select_trigger_traceback ()
                        return False
                        
                else:
                        assert None == self.select_trigger_log (
                                'opened', 'debug'
                                )
                        return True
                        
	def thread_loop_delete (self):
                try:
                        if self.pns_routes != None:
                                self.pns_routes.close ()
                        if self.pns_index != None:
                                self.pns_index.close ()
                except:
                        self.select_trigger_traceback ()
                else:
                        del self.pns_routes, self.pns_index
                        assert None == self.select_trigger_log (
                                'closed', 'debug'
                                )
		self.select_trigger ((
			self.pns_peer.pns_inference_finalize, ()
			))
		del self.pns_peer
                return True

        # in order to understand the code vs. the specifications, I'll go
        # backward and start with what happens last for a directed quatuor
        # in the semantic router
        #
        # but statements are indexed *after* they have been routed
                
                
        # ... Building The Semantic Graph: Map and Index

        def pns_map (self, model):
                self.thread_loop_queue ((
                        self.pns_map_graph, (model[0], model[3])
                        ))

        # >>>

        def pns_map_graph (self, subject, context):
                # encode the context first, then map it
                encoded = '%d:%s,' % (len (context), context)
                self.pns_map_context (subject, context, encoded)
                # recursively index the subject names
                for n, name in self.pns_map_names (
                        unicode (subject, 'UTF-8'), subject
                        ):
                        # and map articulated names to this context too 
                        self.pns_map_context (name, context, encoded)
                        
        def pns_map_context (self, subject, context, encoded):
                if subject == context:
                        return # no identity route
                        
                stored = self.pns_routes.get (subject)
                if stored == None:
                        # new subject, map subject to context
                        self.pns_routes[subject] = encoded + chr (1)
                        return
                        
                # map a subject to a context
                horizon = ord (stored[-1])
                if horizon > 255:
                        # hard limit on the maximum entry length
                        return
                
                if stored.find (encoded) < 0:
                        # new context for this subject
                        self.pns_routes[subject] = ''.join ((
                                encoded, stored[:-1], chr (horizon + 1)
                                ))

        def pns_map_names (self, unicoded, encoded):
                # index a sequence of names to the index
                names = tuple ((
                        (n, encode (n, 'UTF-8'))
                        for n in netunicode.decode (unicoded)
                        ))
                for n, name in names:
                        stored = self.pns_index.get (index)
                        if stored == None:
                                # insert an entry in the index
                                self.pns_index[name] = encoded + chr (1)
                                self.pns_map_names (n, name)
                        elif (
                                ord (stored[-1]) < self.pns_horizon and
                                stored.find (encoded) < 0
                                ):
                                # update an entry with a new index
                                field = set ()
                                stored = public_names.valid (unicode (
                                        encoded + stored[:-1], 'UTF-8'
                                        ),  field, self.pns_horizon)
                                if len (field) < self.pns_horizon:
                                        # but only below the horizon
                                        self.pns_index[name] = (encode (
                                                stored, 'UTF-8'
                                                ) + chr (len (field)))
                return names
                
        # ... Commands 

        def pns_command (self, model):
                # handle a command from a PNS/TCP session
                assert None == self.log (
                        netstring.encode (model), 'command'
                        )
                if model[1]:
                        if model[2]:
                                # walk subject down to contexts, let the user
                                # agent walk the graph up and down at once to
                                # test and weight a subject against a set of
                                # contexts (and not implement that common walk
                                # into the client, but rather articulate it).
                                #
                                contexts = set (netunicode.decode (
                                        unicode (model[2], 'UTF-8')
                                        ))
                                self.thread_loop_queue ((
                                        self.pns_walk_simplest,
                                        (model, contexts)
                                        ))
                                return

                        # walk down the contexts once, in all contexts
                        self.thread_loop_queue ((
                                self.pns_command_predicate, (model,)
                                ))
                        return

                # walk up the names once, for in contexts
                self.thread_loop_queue ((
                        self.pns_command_object, (model,)
                        ))

        # >>> Commands
        
        def pns_command_predicate (self, model):
                # return the mapped routes to the client
                stored = self.pns_routes.get (model[1])
                if stored:
                        model[3] = stored[:-1]                        
                self.select_trigger ((
                        self.pns_peer.pns_tcp_continue, (model, '_')
                        ))

        def pns_command_object (self, model):
                # return the index for the subject submitted
                stored = self.pns_index.get (model[2])
                if stored and (ord (stored[-1]) < self.pns_horizon):
                        # return only indexes beyond the peer's horizon, not
                        # those behind.
                        model[3] = stored[:-1]
                self.select_trigger ((
                        self.pns_peer.pns_tcp_continue, (model, '_')
                        ))
                return

        # ... Statements
                      
        def pns_statement (self, model):
                # PNS/TCP or PNS/UDP statement
                if model[1]:
                        # non-protocol, routes to subscribed circles
                        contexts = set (
                                self.pns_peer.pns_subscribed.keys ()
                                )
                else:
                        # protocol, route to joined circles
                        contexts = set ([
                                d.pns_name for d in
                                self.pns_peer.pns_udp.pns_joined.values ()
                                ])      
                # ... route >>>
                self.thread_loop_queue ((
                        self.pns_walk_simplest, (model, contexts)
                        ))

        # >>> The Semantic Walk
                                
	def pns_walk_simplest (self, model, contexts):
                subject = unicode (model[0] or model[1], 'UTF-8')
		walked = set ((subject, ))
                if subject in contexts:
                        routes = {subject: set ((subject, ))}
                else:
                        routes = {}
                paths = self.pns_walk_down (subject, contexts)
                if paths:
                        routes.setdefault (subject, set ()).update (paths)
                if len (routes) > 0:
                        self.pns_walk_out (model, routes)
                        return
                        
                names = list (
                        netunicode.decode (subject)
                        ) or [subject]
                self.thread_loop_queue ((
                        self.pns_walk_simple,
                        (model, contexts, walked, routes, names)
                        ))
                        
	def pns_walk_down (self, name, contexts):
                stored = self.pns_routes.get (encode (name, 'UTF-8'))
                if stored and (ord (stored[-1]) < self.pns_horizon):
		        return contexts & set (netunicode.decode (
                                unicode (stored[:-1], 'UTF-8')
                                ))
                
                return NULL_SET
                        
        def pns_walk_up (self, names, walked):
                index = {}
                for name in names:
                        stored = self.pns_index.get (encode (name, 'UTF-8'))
                        if stored and (ord (stored[-1]) < self.pns_horizon):
                                for n in (set (netunicode.decode (unicode (
                                        stored[:-1], 'UTF-8'
                                        ))) - walked):
                                        index.setdefault (
                                                n, set()
                                                ).add (name)
                return index
                                        
	def pns_walk_simple (
                self, model, contexts, walked, routes, names
                ):
                assert None == self.select_trigger_log (
                        '<walk-simple horizon="%d" walked="%d"/>'
                        '<![CDATA[%s]]!>' % (
                                len (names), len (walked),
                                netstring.encode (model)
                                ), 'debug'
                        )
                for name in names:
                        if name in walked:
                                continue
                                
                        walked.add (name)
                        if name in contexts:
                                routes.setdefault (name, set ()).add (name)
                        paths = self.pns_walk_down (name, contexts)
                        if paths:
                                routes.setdefault (name, set ()).update (paths)
                        if len (walked) >= self.pns_horizon:
                                # horizon reached, walk out
                                self.pns_walk_out (model, routes)
                                return
                                 
                names = self.pns_walk_up (names, walked)
                if len (names) == 0:
                        # no more index to walk, walk out
                        self.pns_walk_out (model, routes)
                        return
                        
                names = [r[1] for r in pns_weight_names (names)]
                self.thread_loop_queue ((
		        self.pns_walk_simple,
                        (model, contexts, walked, routes, names)
			))  # >>> do another simple step 

        def pns_walk_out (self, model, routes):
                # continue the commands, drop the statements
                routes = pns_weight_routes (routes)
                assert None == self.select_trigger_log (
                        '<walk-out routes="%d"/>'
                        '<![CDATA[%s]]!><![CDATA[%s]]!>' % (
                                len (routes),
                                netstring.encode (model),
                                encode (netunicode.encode (
                                        [r[1] for r in routes]
                                        ), 'UTF-8')
                                ), ''
                        )
                self.select_trigger ((
                        self.pns_walk_continue, (model, routes)
                        ))

        # ... PNS/Semantic walker asynchronous continuation

        def pns_walk_continue (self, model, routes):
                # handle the result of the semantic walk for all kind of
                # statements coming from all directions, including the user
                # command (,p,o).
                #
                if model[0] == '':
                        # user command, send response to the PNS/TCP session
                        # as an ordered set of contexts and related names.
                        model[3] = encode (netunicode.encode ([
                                u"%d:%s,%s" % (
                                        len (c), c, 
                                        netunicode.encode (n)
                                        )
                                for w, c, n in routes
                                ]), 'UTF-8')
                        self.pns_peer.pns_tcp_continue (model, '_')
                        return
                        
                # statements
                if model[3] and (len (model) > 4 or model[2] == ''):
                        # named statement, index the subject and map it to
                        # its original context if the statement comes from
                        # a PNS/TCP session or is a question
                        #
                        self.pns_map (model)
                if len (model) > 4:
                        # echo only PNS/TCP statements routed, not PNS/UDP
                        # statements relayed.
                        #
                        self.pns_peer.pns_tcp_continue (model, '.')
                if len (routes) == 0:
                        return
                        
                # if any, find the best routes subscribed
                best = routes[0][0]
                circles = (
                        self.pns_peer.pns_subscribed[context]
                        for context in (
                                encode (r, 'UTF-8') 
                                for w, r, n in routes if w == best
                                )
                        if self.pns_peer.pns_subscribed.has_key (context)
                        )
                if not model[1]:
                        # route protocol statement to circles joined only
                         circles = [
                                c for c in circles
                                if self.pns_peer.pns_udp.pns_joined.has_key (
                                        c.pns_right
                                        )
                                ]
                # route to the best circles
                for circle in circles:
                        circle.pns_statement (model)


# prepares a map returned by the walker
                                        
def pns_weight_names (graph):
        graph = [(len (names), name) for name, names in graph.items ()]
        graph.sort ()
        graph.reverse ()
        return graph


def pns_weight_routes (graph):
        mapped = {}
        for item in graph.items ():
                for context in item[1]:
                        mapped.setdefault (context, []).append (item[0])
        ordered = [
                (len (names), context, names) 
                for context, names in mapped.items ()
                ]
        ordered.sort ()
        ordered.reverse ()
        return ordered


# Note about this implementation
#
# The Semantic Walk is a simple algorithm that should scale from transient
# peer with limited graph to persistent ones maintaining unlimited
# and possibly huge graphs. This implementation *will* be relatively slow
# until netstring.decode is optimized (in a C module along the other
# obvious bottlenecks) and some tuning of bsddb3 caching is done.
#
# However, what matters more is that it produces relevant routes ;-)
#
#
# Roadmap
#
# A possible development is the split in an index thread and independant 
# walker threads. This would allow to walk a consistent graph in parallel
# without waiting for the mapper. The graph can be written by only one thread.
# and share the workload of routing between a pool of threads, or at least
# one for maping and one for walking. However, given the Global Interpreter
# Lock in Python, this would only yield *real* improvements if the time
# consuming methods were to be pushed in a C module, releasing the GIL most
# of the time, leaving allmost just the asynchronous I/O and thread logic to
# handle by Python code. The practical path is to first rewrite the pns_model
# and netstring_decode in a C module, while investigating several thread
# loops. Finally wrap bdsdb interfaces with C for all threaded methods
# including the thread_loop itself.
#
#
# Articulate!
#
# The first obvious applications are articulators that can walk the semantic
# graph and/or the quatuor cache of the PNS peer. What makes PNS/Semantic
# really "cool" is that it lets user agents articulate the search as their
# application requires, not as some query language designer came with.
#
# PNS/Inference is full text search: it reduces subjects to a non dispersed
# semantic graph mapped to a set of contexts, in a simple and consistent
# process, and let user agents walk that graph in all directions as far
# and in the path they choose.
#
# The benefit for the developpers is big: they can develop an original
# algorithm that enhances the relevance of results significantly, user
# as much resources available for their applications, yet rely on a stable
# and safe protocol to integrate in the user's network, in its semantic
# graph.
#
# The benefit for both the users and the developpers is that they are also
# assured that they both own the Public Name System. And not some big
# corporate business (here pick your favorite ;-) trying to sell bloatware,
# hogware ... or your profile.
#
# For a sample semantic articulator, see pns_articulator.py
#
#
# Other applications
#
# Nothing - quite the contrary - refrains the PNS user agents to integrate
# their own PNS/Inference engine, using another set of metadata and 
# possibly another semantic horizon. It makes sense to use the same
# algorithm and data model inside the user agents to develop specialised
# search articulation or to maintain the diversity of semantic horizon
# for the application's users.
