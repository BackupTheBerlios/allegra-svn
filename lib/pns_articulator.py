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

from allegra import netstring, finalization, pns_model


def pns_articulate_route (encoded):
        names = netstring.netlist (encoded)
        name = pns_model.pns_name (netstring.encode (names[1:]), set ())
        return (names[0], name)
        

class PNS_articulator:

        def __init__ (self, client=None, commands=None, contexts=None):
                self.pns_client = client
                self.pns_commands = commands or {}
                self.pns_contexts = contexts or {}
                
        def pns_command (self, articulated, handler):
                assert (
                        type (articulated) == tuple and 
                        len (articulated) == 3 and
                        articulated[0] == ''
                        )
                try:
                        model = self.pns_commands[articulated]
                except:
                        self.pns_client.pns_command (
                                articulated, (
                                        lambda
                                        resolved, model, s=self, h=handler:
                                        s.pns_command_continue (
                                                resolved, model, h
                                                )
                                        )
                                )
                else:
                        if handler != None:
                                handler (articulated, model)
                                
        def pns_command_continue (self, resolved, model, handler=None):
                # cache commands ...
                if model[3] == '':
                        self.pns_commands[resolved] = None
                elif resolved[1] == '' or resolved[2] == '':
                        # ... as sets for contexts and indexes
                        self.pns_commands[resolved] = (
                                model[3], set (netstring.netlist (model[3]))
                                )
                else:
                        # ... as lists of sets for routes
                        self.pns_commands[resolved] = [
                                pns_articulate_route (encoded)
                                for encoded in 
                                netstring.netlist (model[3])
                                ]
                if handler != None:
                        handler (resolved, self.pns_commands[resolved])
                return False

        def pns_statement (self, articulated, context, handler):
                assert (
                        type (articulated) == tuple and 
                        len (articulated) == 3 and
                        not (articulated[0] == '' or articulated[1] == '')
                        )
                try:
                        model = self.pns_contexts[context][articulated]
                except:
                        #if articulated[2] != '':
                        #        # cache statements now!
                        #        self.pns_contexts.setdefault (
                        #                articulated[3], {}
                        #                )[articulated] = articulated
                        self.pns_client.pns_statement (
                                articulated, context, (
                                        lambda
                                        resolved, model, s=self, h=handler:
                                        s.pns_statement_continue (
                                                resolved, model, h
                                                )
                                        )
                                )
                else:
                        if handler != None:
                                handler (articulated, model)
                
        def pns_statement_continue (self, resolved, model, handler=None):
                if model[4] != '_':
                        # TODO: ... handle '.', '!' and '?' 
                        return False

                if resolved[2] == '':
                        # cache question's answers.
                        self.pns_contexts.setdefault (
                                model[3], {}
                                )[resolved] = model
                if handler != None:
                        handler (resolved, model)
                return True


# The Semantic Walk: get articulated indexes and contexts, and for each
# context considered as a subject get a set of statement.
#
# 1. Walk up the index as much as possible, until no index is
#    available for the current articulation. In effect, read as
#    much as possible of a unique articulation.
#
# 2. Then start to walk the index down for one or more contexts
#    articulating the indexes when no context is available. In effect
#    get a set of possible contexts for the original articulation.
#
# 3. If there are more than one contexts available, walk from
#    the original subject down to those contexts and get the routes
#    sorted by the peer, and use each context as subject. In effect
#    weight dissent.
#
#    If there is one context found, use it as subject
#
#    If no context is available, use the index as subject
#
# 4. Retrieve all subjects.
#
# Note that a PNS/TCP user agent does not have to actually implement
# anything else than netstrings and TCP. Set types are not available
# everywhere and PNS agents don't actually require them to articulate
# a usefull search processes.


class PNS_articulate (finalization.Finalization):

        pns_index = None
        
        def __init__ (
                self, articulator, articulated, 
                predicates=None, context='', HORIZON=15
                ):
                self.pns_predicates = predicates
                self.pns_context = context
                self.pns_contexts = set ()
                self.pns_subjects = []
                self.pns_sat = []
                self.PNS_HORIZON = HORIZON
                PNS_articulate_names (
                        articulator, articulated
                        ).finalization = self.pns_articulate_names
                        
        def pns_articulate_names (self, finalized):
                if len (finalized.pns_indexes) > 1:
                        self.pns_index = pns_model.pns_name (
                                netstring.encode (list (
                                        finalized.pns_indexes
                                        )), set ()
                                )
                elif len (finalized.pns_indexes) > 0:
                        self.pns_index = tuple (finalized.pns_indexes)[0]
                if len (finalized.pns_contexts) > 1:
                        # TODO: add PNS route here
                        #
                        # finalized.pns_articulator.pns_command ((
                        #        '', finalized.pns_articulated, 
                        #        netrstrings_encode (pns_contexts)
                        #        ), self.pns_resolve_routes)
                        #
                        if self.pns_predicates and (
                                self.PNS_HORIZON > len (
                                        finalized.pns_contexts
                                        )
                                ):
                                for subject in finalized.pns_contexts:
                                        PNS_articulate_subject (
                                                finalized.pns_articulator,
                                                subject,
                                                self.pns_predicates,
                                                self.pns_context
                                                ).finalization = \
                                                self.pns_articulate_subject
                elif len (finalized.pns_contexts) > 0:
                        # one single context: use it as subject
                        PNS_articulate_subject (
                                finalized.pns_articulator,
                                list (finalized.pns_contexts)[0],
                                self.pns_predicates,
                                self.pns_context
                                ).finalization = self.pns_articulate_subject
                # get all SAT available for articulated names
                for name in finalized.pns_contexts.union (
                        set (finalized.pns_indexes)
                        ):
                        if len (tuple (netstring.decode (name))) > 0:
                                finalized.pns_articulator.pns_statement (
                                        (name, 'sat', ''), '', 
                                        self.pns_resolve_sat
                                        )
                finalized.pns_articulator = None
                
        def pns_articulate_subject (self, finalized):
                if finalized.pns_objects:
                        self.pns_subjects.append ((
                                finalized.pns_subject,
                                finalized.pns_objects
                                ))
                        self.pns_contexts.update (finalized.pns_contexts)
                finalized.pns_articulator = None
                
        def pns_resolve_sat (self, resolved, model):
                if model[2] == '':
                        return
                        
                statements = list (netstring.decode (model[2]))
                if len (statements) > 0:
                        for co in statements:
                                c, o = netstring.decode (co)
                                self.pns_sat.append ((
                                        resolved[0], resolved[1], 
                                        o, c, '_'
                                        ))
                else:
                        c, o = netstring.decode (model[2])
                        self.pns_sat.append ((
                                resolved[0], resolved[1], o, c, '_'
                                ))
                                

class PNS_articulate_names (finalization.Finalization):
        
        # The real search.
        #
        # Walks the semantic graph up and down for 
        
        def __init__ (
                self, articulator, articulated, HORIZON=126
                ):
                self.pns_articulator = articulator
                self.pns_articulated = articulated
                self.pns_indexes = set ()
                self.pns_contexts = set ((articulated, ))
                self.PNS_HORIZON = HORIZON
                # walk up the indexes ...
                self.pns_articulator.pns_command (
                        ('', '', articulated), self.pns_resolve_index
                        )
                                
        def pns_resolve_index (self, resolved, model):
                self.pns_indexes.add (resolved[2])
                if model == None:
                        # unique or unknown articulation, walk down ...
                        self.pns_articulator.pns_command (
                                ('', resolved[2], ''), 
                                self.pns_resolve_context
                                )
                        return

                # continue to walk up the indexes ...
                self.pns_contexts.add (model[0])
                if len (self.pns_contexts) < self.PNS_HORIZON:
                        self.pns_articulator.pns_command (
                                ('', '', model[0]), 
                                self.pns_resolve_index
                                )
                                
        def pns_resolve_context (self, resolved, model):
                if model != None:
                        # Context found for an articulation
                        self.pns_contexts.update (model[1])
                        return # stop.

                # no context available, articulate the name resolved
                names = list (netstring.decode (resolved[1]))
                if len (names) == 0:
                        # nothing to articulate, if there are no contexts
                        # available yet, walk up
                        if not (
                                resolved[1] in self.pns_indexes
                                ) and len (self.pns_contexts) == 0:
                                self.pns_articulator.pns_command (
                                        ('', '', resolved[1]), 
                                        self.pns_resolve_index
                                        )
                        return
                        
                # get the contexts for each newly articulated name
                for name in names:
                        if name in self.pns_indexes:
                                continue
                                
                        self.pns_articulator.pns_command (
                                ('', name, ''), 
                                self.pns_resolve_context
                                )
                                

class PNS_articulate_subject (finalization.Finalization):
        
        # get all objects and contexts for a given subject, then finalize
        
        def __init__ (
                self, articulator, subject, predicates=('sat', ), context=''
                ):
                self.pns_articulator = articulator
                self.pns_subject = subject
                self.pns_predicates = predicates
                self.pns_objects = []
                self.pns_contexts = set ()
                self.pns_articulator.pns_command (
                        ('', subject, ''), self.pns_resolve_contexts
                        )

        def pns_resolve_contexts (self, resolved, model):
                if model == None:
                        return
                        
                self.pns_contexts.update (model[1])
                for predicate in self.pns_predicates:
                        self.pns_articulator.pns_statement (
                                (resolved[1], predicate, ''), '',
                                self.pns_resolve_predicate
                                )

        def pns_resolve_predicate (self, resolved, model):
                if model[3]:
                        # single contextual statement
                        self.pns_objects.append (model)
                elif model[2]:
                        # multiple contextual statements
                        statements = list (netstring.decode (model[2]))
                        if len (statements) > 0:
                                for co in statements:
                                        c, o = netstring.decode (co)
                                        self.pns_objects.append ((
                                                resolved[0], resolved[1], 
                                                o, c, '_'
                                                ))
                        else:
                                c, o = netstring.decode (model[2])
                                self.pns_objects.append ((
                                        resolved[0], resolved[1], o, c, '_'
                                        ))
                                

if __name__ == '__main__':
        import sys, time
        sys.stderr.write (
                'Allegra PNS/TCP Articulator'
                ' - Copyright 2005 Laurent A.V. Szyster\n'
                )
                
        from exceptions import StopIteration
        from allegra import pns_client
        
        class PNS_pipe (pns_client.PNS_client_channel):
                
                def __init__ (self, ip, pipe):
                        self.pns_start = time.time ()
                        self.pns_pipe = pipe
                        pns_client.PNS_client_channel.__init__ (self, ip)
                        self.tcp_connect ()
                        
                def pns_peer (self, ip):
                        if ip:
                                encoded = '%d:%s,0:,0:,0:,' % (len (ip), ip)
                                sys.stdout.write ('%d:%s,' % (
                                        len (encoded), encoded
                                        ))
                                self.pns_articulator = PNS_articulator (self)
                                self.pns_articulate ()
                                return
                                
                        assert None == self.log (
                                '<close sent="%d" received="%d" seconds="%f"'
                                '/>' % (
                                        self.pns_sent, self.pns_received,
                                        time.time () - self.pns_start
                                        ), ''
                                )
                        self.pns_articulator.pns_client = None
                        del self.pns_articulator
                        
                def pns_articulate (self):
                        try:
                                encoded = self.pns_pipe.next ()
                                
                        except StopIteration:
                                # no more statements to handle, close when
                                # done ...
                                self.pns_close_when_done = True
                                return

                        model = list (netstring.decode (encoded))
                        if len (model) != 4:
                                self.pns_close_when_done = True
                                return
                        
                        if model[1] == model[2] == model[3] == '':
                                PNS_walk (self.pns_articulator, model[0])
                        elif model[2] != '' or model[3] != '':
                                self.pns_articulator.pns_articulate (
                                        tuple (model[:3]), model[3]
                                        )
                        else:
                                pass
                        
        if len (sys.argv) > 1:
                ip = sys.argv[1]
        else:
                ip = '127.0.0.1'
        PNS_pipe (ip, netstring.netpipe (lambda: sys.stdin.read (4096)))
        from allegra import async_loop
        try:
                async_loop.loop ()
        except:
                async_loop.loginfo.loginfo_traceback ()
        #
        # Allegra PNS/TCP Articulator
        #
        # The reference implementation of a PNS/TCP articulator, it is one
        # usefull module to develop PNS articulators, but also a nice command
        # line tool feed a peer relevantly and "walk" its graph automatically.
        #
        # As a pipe it reads from STDIN a sequence of netstrings, 
        # first one as the session name and pipes the others to a PNS/TCP
        # session, then writes relevant statements coming back from the peer
        # to STDOUT and drops the irrelevant statements to STDERR. Example:
        #
        #    python pns_client.py < session.pns 1> signal 2> noise
        #
        # you may also pass the IP address of the PNS peer
        #
        #    python pns_client.py 192.168.1.1 < session.pns 1> signal 2> noise
        #
        # but for an interactive prompt, use instead pns_prompt.py.
