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
        netstring, loginfo, finalization, pns_model, pns_client
        )


def pns_articulate_route (encoded):
        names = netstring.netlist (encoded)
        name = pns_model.pns_name (netstring.encode (names[1:]), set ())
        return (names[0], name)
        

class PNS_articulator (finalization.Finalization):
        
        "a keep-alive caching PNS articulator"
        
        PNS_CLIENT = pns_client.PNS_client ()
        
        pns_keep_alive = True

        def __init__ (
                self, addr=('127.0.0.1', 3534), commands=None, contexts=None
                ):
                self.pns_tcp_addr = addr
                self.pns_client = self.PNS_CLIENT (addr, self.pns_peer)
                self.pns_commands = commands or {}
                self.pns_contexts = contexts or {}

        def pns_peer (self, resolved, model):
                ip = model[3]
                if ip:
                        return True # opened, keep this handler
                        
                if self.pns_keep_alive:
                        self.pns_client = None
                else:
                        self.pns_client = self.PNS_CLIENT (
                                addr, self.pns_peer
                                )
                return False # closed, release this handler
                
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


def pns_walk_out (subject, contexts):
        assert None == loginfo.log (netstring.encode ((
                subject, netstring.encode (contexts)
                )), 'pns-walk-out')

class PNS_walk (finalization.Finalization):
        
        "walk the PNS graph to find subject(s) and context(s)"

        def __init__ (
                self, name, articulator, walk_out=pns_walk_out, HORIZON=31
                ):
                self.pns_name = name
                self.pns_articulator = articulator
                self.pns_walk_out = walk_out
                self.PNS_HORIZON = HORIZON
                #
                self.pns_walked = set ((name,))
                self.pns_articulator.pns_command (
                        ('', '', name), self.pns_resolve_index
                        ) # walk the indexes ...

        def pns_resolve_index (self, resolved, model):
                if model != None:
                        # known name
                        name = model[0]
                        if (
                                len (self.pns_walked) > self.PNS_HORIZON or 
                                name in self.pns_walked
                                ):
                                return
                        
                        # new and below the horizon
                        self.pns_walked.add (name)
                        self.pns_articulator.pns_command (
                                ('', name, ''), 
                                self.pns_resolve_context
                                ) # walk the contexts ...
        
                # unknown name
                names = tuple (netstring.decode (resolved[2]))
                if len (names) == 0:
                        # inarticulated
                        self.pns_articulator.pns_command (
                                ('', name, ''), 
                                self.pns_resolve_context
                                ) # walk the contexts ...
                        return             
                        
                # for each name articulated
                for name in names:
                        if name in self.pns_walked:
                                continue
                        
                        if len (self.pns_walked) > self.PNS_HORIZON:
                                break
                        
                        # new and below the horizon
                        self.pns_walked.add (name)
                        self.pns_articulator.pns_command (
                                ('', name, ''), 
                                self.pns_resolve_context
                                ) # walk the contexts ...                        
                                
        def pns_resolve_context (self, resolved, model):
                if model != None:
                        # context(s) found
                        self.pns_walk_out (resolved[1], model[1])
                        return # stop walking.

                # no context known
                for name in tuple (netstring.decode (resolved[1])):
                        if name in self.pns_walked:
                                continue
                                
                        if len (self.pns_walked) >= self.PNS_HORIZON:
                                break # beyond the horizon, stop walking.

                        # new and below the horizon 
                        self.pns_walked.add (name)
                        self.pns_articulator.pns_command (
                                ('', '', name), 
                                self.pns_resolve_index
                                ) # walk up the indexes ...


def pns_find_out (resolved, model):
        if model[2] != '0:,':
                assert None == loginfo.log (
                        netstring.encode (model), 'pns-find-out'
                        )
                
class PNS_search (PNS_walk):
        
        def __init__ (
                self, subject, articulator, predicate='sat', 
                find_out=pns_find_out, HORIZON=31
                ):
                self.pns_predicate = predicate
                self.pns_find_out = find_out
                PNS_walk.__init__ (
                        self, subject, articulator, 
                        self.pns_walk_out, HORIZON
                        )

        def pns_walk_out (self, subject, contexts):
                self.pns_articulator.pns_statement (
                        (subject, self.pns_predicate, ''), '',
                        self.pns_find_out
                        )


class PNS_find (finalization.Finalization):
        
        "walk the PNS graph to find answer(s) for a subject and a predicate"
        
        def __init__ (
                self, subject, articulator, predicate='sat', 
                find_out=pns_find_out, HORIZON=31
                ):
                self.pns_name = subject
                self.pns_articulator = articulator
                self.pns_predicate = predicate
                self.pns_find_out = find_out
                self.PNS_HORIZON = HORIZON
                #
                self.pns_walked = set ((subject,))
                self.pns_articulator.pns_statement (
                        (subject, predicate, ''), '', 
                        self.pns_resolve_statement
                        ) # ask an open question about the subject ...
                                
        def pns_resolve_statement (self, resolved, model):
                if model[2] != '0:,':
                        # context(s) and object(s) found
                        self.pns_find_out (resolved, model)
                        # stop walking.
                        return
                
                # no answer 
                self.pns_articulator.pns_command (
                        ('', resolved[0], ''), 
                        self.pns_resolve_context
                        ) # walk up the context first ...
                return
                
        def pns_resolve_context (self, resolved, model):
                if model == None:
                        # no context
                        self.pns_articulator.pns_command (
                                ('', '', resolved[1]), 
                                self.pns_resolve_index
                                ) # walk up the index second ...
                        return
                
                question = (resolved[1], self.pns_predicate, '')
                for context in model[1]:
                        #if context in self.pns_walked:
                        #        continue
                        #
                        # self.pns_walked.add (context)
                        self.pns_articulator.pns_statement (
                                question, '', self.pns_resolve_statement
                                )
                
        def pns_resolve_index (self, resolved, model):
                if model != None:
                        # known name
                        self.pns_articulator.pns_statement (
                                (resolved[2], self.pns_predicate, ''), '',
                                self.pns_resolve_statement
                                ) 
                                # ask an open question about it ...
                        return

                # unknown subject for this predicate, articulate ...
                for name in tuple (netstring.decode (resolved[2])):
                        if name in self.pns_walked:
                                continue
                                
                        if len (self.pns_walked) >= self.PNS_HORIZON:
                                break # beyond the horizon, stop walking.

                        # for each new name below the horizon 
                        self.pns_walked.add (name)
                        self.pns_articulator.pns_command (
                                ('', '', name), 
                                self.pns_resolve_index
                                ) # walk up the indexes once ...


# Note
#
# This is a set of fairly non-trivial state-machines that support a cache
# of PNS/Inference command responses allready parsed and transformed as
# sets. The purpose is to save CPU at the expense of RAM when the application
# repeatedly walks over the same part its PNS context graph. Another benefit
# is of course that using a PNS_articulator reduces the traffic with the
# metabase and its workload.
#
# Last but not least, two articulators can "speak" over the same client.
#
# So, Allegra's PNS client implementation is concise and will not pound
# stupidely at the metabase asking the same questions over and over. The
# fact that a PNS peer does filter out redundant statement when distributing
# them does not mean that its user agents should be verbose.

if __name__ == '__main__':
        import sys, time
        sys.stderr.write (
                'Allegra PNS/TCP Articulator'
                ' - Copyright 2005 Laurent A.V. Szyster\n'
                )
                
        from allegra import async_loop
        
        # TODO: ... PNS_pipe
        
        ip = '127.0.0.1'
        port = 3534
        if len (sys.argv) > 1:
                if len (sys.argv) > 2:
                        port = int (sys.argv[2])
                ip = sys.argv[1]
        articulator = PNS_articulator ((ip, port))
        netpipe = netstring.netpipe (lambda: sys.stdin.read (4096))
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
        

# Note
#
# The trouble with walking is that each set generations will be guaranteed
# to have a latency of at least the select.poll timeout. That's good for
# a high-performance peer that generates a lot of walkers in parallel, but
# it will impair a single user walking alone.
#
# 
# only one user should expects