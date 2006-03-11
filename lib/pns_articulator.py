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
        
        "a caching PNS/Inference articulator"

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


def pns_walk_out (subject, contexts):
        assert None == loginfo.log (netstring.encode ((
                subject, netstring.encode (contexts)
                )), 'pns-walk-out')

class PNS_walk (finalization.Finalization):
        
        "walk the PNS graph to find context(s) for a name"

        def __init__ (
                self, name, articulator, walk_out=pns_walk_out, HORIZON=126
                ):
                self.pns_name = name
                self.pns_articulator = articulator
                self.pns_walk_out = walk_out
                self.PNS_HORIZON = HORIZON
                #
                self.pns_walked = set ((name,))
                self.pns_articulator.pns_command (
                        ('', '', name), self.pns_resolve_index
                        ) # walk up the indexes ...
                                
        def pns_resolve_index (self, resolved, model):
                if model == None:
                        # unknown name
                        self.pns_articulator.pns_command (
                                ('', resolved[2], ''), 
                                self.pns_resolve_context
                                ) # walk up the contexts ...
                        return

                # known name
                name = model[0]
                if name in self.pns_walked:
                        return
                
                self.pns_walked.add (name)
                self.pns_articulator.pns_command (
                        ('', '', name), 
                        self.pns_resolve_index
                        ) # walk up the indexes ...
                                
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
        
        