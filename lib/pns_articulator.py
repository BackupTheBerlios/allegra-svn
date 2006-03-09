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

from allegra import netstring, loginfo, finalization, pns_model


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
# 1. Walk "up" the graph as much as possible, until no index is
#    available for the current articulation. In effect, read as
#    much as possible of a unique articulation.
#
# 2. Then start to walk the graph "down" for one or more contexts
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

class Walk (finalization.Finalization):

        PNS_HORIZON = 126
        pns_predicate = 'sat'
        
        def __init__ (self, articulator, walked):
                self.pns_articulator = articulator
                self.pns_walked = walked
                self.pns_names = set ((walked,))
                self.pns_articulator.pns_command (
                        ('', '', walked), self.pns_resolve_index
                        ) # walk up the indexes ...
                                
        def pns_resolve_index (self, resolved, model):
                if model == None:
                        # unique or unknown articulation
                        self.pns_articulator.pns_command (
                                ('', resolved[2], ''), 
                                self.pns_resolve_context
                                ) # walk up the contexts ...
                        return

                # known name
                walked = model[0]
                if not (
                        walked in self.pns_names
                        ) and len (self.pns_names) < self.PNS_HORIZON:
                        # new and below the horizon
                        self.pns_names.add (walked)
                        self.pns_articulator.pns_command (
                                ('', '', walked), 
                                self.pns_resolve_index
                                ) # walk up the indexes ...
                                
        def pns_resolve_context (self, resolved, model):
                walked = resolved[1]
                if model != None:
                        # Context(s) found
                        if len (tuple (netstring.decode (walked))) > 0:
                                # for an articulation
                                question = (walked, self.pns_predicate, '')
                                for context in iter (
                                        model[1].difference(self.pns_names)
                                        ):
                                        self.pns_articulator.pns_statement (
                                                question, context,
                                                self.pns_resolve_statement
                                                ) # ask statements ...
                        return # stop walking.

                # no context available, 
                names = tuple (netstring.decode (walked))
                if len (names) > 0:
                        # get the contexts for each articulated name
                        for name in names:
                                if name in self.pns_names:
                                        continue
                                        
                                if len (self.pns_names) >= self.PNS_HORIZON:
                                        break
                                
                                self.pns_names.add (name)
                                self.pns_articulator.pns_command (
                                        ('', '', name), 
                                        self.pns_resolve_index
                                        ) # walk up the indexes ...
                                #self.pns_articulator.pns_command (
                                #        ('', name, ''), 
                                #        self.pns_resolve_context
                                #        ) # walk up the contexts ...
                        return

                # inarticulated
                #if not (
                #        walked in self.pns_names
                #        ) and len (self.pns_names) < self.PNS_HORIZON:
                #        # new and below the horizon
                #        self.pns_names.add (walked)
                #        self.pns_articulator.pns_command (
                #                ('', '', walked), 
                #                self.pns_resolve_index
                #                ) # walk up the indexes ...

        def pns_resolve_statement (self, resolved, model):
                assert None == loginfo.log (
                        netstring.encode (model), 'Walk'
                        )


def test_walk (walked, pns, horizon=16):
        Walk.PNS_HORIZON = horizon
        return Walk (PNS_articulator (pns (('127.0.0.1', 3534))), walked)
        

if __name__ == '__main__':
        import sys, time
        sys.stderr.write (
                'Allegra PNS/TCP Articulator'
                ' - Copyright 2005 Laurent A.V. Szyster\n'
                )
                
        from allegra import async_loop, pns_client
        
        class PNS_pipe (pns_client.PNS_pipe):
                
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
                                Walk (self.pns_articulator, model[0])
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
        async_loop.dispatch ()
        assert None == finalization.collect ()
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
        
        