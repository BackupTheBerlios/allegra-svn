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

from allegra import netstring, async_net, tcp_client


class PNS_client_channel (
        async_net.Async_net, tcp_client.TCP_client_channel
        ):
        
        # a PNS client to implement multiplexing user agents like a resolver.
        
        def __init__ (self):
                self.pns_commands = {}
                self.pns_contexts = {}
                self.pns_subscribed = {}
                async_net.Async_net.__init__ (self)
                
        def __repr__ (self):
                return 'pns-client id="%x"' % id (self)

        def handle_close (self):
                # callback all pending statement handlers with echo, command
                # or peer ip handlers with void responses, then callback
                #
                for context, handlers in self.pns_subscribed.items ():
                        for handler in handlers:
                                handler (None)
                for context, statements in self.pns_contexts.items ():
                        for resolved, handlers in statements.items ():
                                model = list (resolved)
                                model.append (context)
                                model.append ('.')
                                for handler in handlers:
                                        handler (resolved, model)
                for resolved, handlers in self.pns_commands.items ():
                        model = list (resolved)
                        model.append ('')
                        model.append ('_')
                        for handler in handlers:
                                handler (resolved, model)
                self.pns_commands = {}
                self.pns_contexts = {}
                self.pns_subscribed = {}
                self.pns_peer ('')
                self.close ()
                del self.async_net_continue

        def async_net_continue (self, encoded):
                model = list (netstring.decode (encoded))
                if len (model) < 5:
                        assert None == self.log (
                                encoded, 'invalid-peer-statement'
                                )
                        self.handle_close ()
                        return
                        
                self.pns_peer (model[0])
                self.async_net_continue = self.pns_continue
                
        pns_sent = pns_received = 0
        pns_close_when_done = False
        
        def pns_peer (self, ip):
                assert None == self.log (
                        'peer ip="%s"' % ip, 'debug'
                        )
                        
        def pns_send (self, encoded):
                self.async_net_push ((encoded,))
                self.pns_sent += 1

        def pns_join (self, context, ip, handler):
                if self.pns_subscribed.has_key (context):
                        self.pns_subscribed[context].append (handler)
                else:
                        self.pns_subscribed[context] = [handler]
                self.pns_send (netstring.encode ((
                        context, '', ip, context
                        )))

        def pns_subscribe (self, context, handler):
                if self.pns_subscribed.has_key (context):
                        self.pns_subscribed[context].append (handler)
                else:
                        self.pns_subscribed[context] = [handler]
                        self.pns_send (netstring.encode ((
                                context, '', '', context
                                )))

        def pns_quit (self, context, handler):
                if self.pns_subscribed.has_key (context):
                        self.pns_subscribed[context].remove (handler)
                        if len (self.pns_subscribed[context]) == 0:
                                del self.pns_subscribed[context]
                                self.pns_send (netstring.encode ((
                                        '', '', '', context
                                        )))

        def pns_command (self, model, handler=None):
                return self.pns_resolve (
                        model, '', handler, 
                        self.pns_commands.setdefault (model, [])
                        )
                        
        def pns_statement (self, model, context='', handler=None):
                assert context == '' or not (
                        model[1] == '' and model[0] == context
                        )
                return self.pns_resolve (
                        model, context, handler, 
                        self.pns_contexts.setdefault (
                                context, {}
                                ).setdefault (model, [])
                        )

        def pns_resolve (self, model, context, handler, handlers):
                handlers.append (handler or self.pns_signal)
                if len (handlers) == 1:
                        # send the statement if it is not redundant
                        encoded = netstring.encode (model)
                        if context:
                                encoded += '%d:%s,' % (len (context), context)
                        else:
                                encoded += '0:,'
                        self.pns_send (encoded)
                        return True
                        
                return False

        def pns_continue (self, encoded):
                # Note that there is no validation of the PNS statements
                # because they are trusted to be valid. A client *may*
                # validate, the peer *must* anyway.
                # 
                self.pns_received += 1
                model = list (netstring.decode (encoded))
                if len (model) != 5:
                        assert None == self.log (
                                encoded, 'invalid-peer-statement'
                                )
                        self.handle_close ()
                        return
                        
                self.pns_multiplex (model)
                resolved = tuple (model[:3])
                if '' == model[0]:
                        if '' == model[1] == model[2]:
                                # protocol command: unsubscribed
                                return
                                
                        # index, context and route
                        handlers = self.pns_commands.get (resolved)
                        if handlers == None:
                                assert None == self.log (
                                        encoded, 
                                        'unsollicited-command-response'
                                        )
                                self.handle_close ()
                                return

                        self.pns_commands[resolved] = [
                                h for h in handlers if h (resolved, model)
                                ]
                        if len (self.pns_commands[resolved]) == 0:
                                del self.pns_commands[resolved]
                elif '' == model[1] and model[0] == model[3]:
                        # protocol
                        pass
                else:
                        # statements
                        statements = self.pns_contexts.setdefault (
                                model[3], {}
                                )
                        handlers = statements.get (resolved)
                        if handlers == None:
                                # test for a question's answer handler
                                resolved = (model[0], model[1], '')
                                handlers = statements.get (resolved)
                                if handlers == None:
                                        # irrelevant statement
                                        self.pns_noise (model)
                                        return
                                
                        # relevant statements, handle and refresh the handlers list
                        statements[resolved] = [
                                h for h in handlers if h (resolved, model)
                                ]
                        # then clean up ...
                        if len (statements[resolved]) == 0:
                                del statements[resolved]
                        if len (statements) == 0:
                                del self.pns_contexts[model[3]]
                if (
                        self.pns_close_when_done and 
                        len (self.pns_commands) == 0 and
                        len (self.pns_contexts) == 0 and
                        len (self.pns_subscribed) == 0
                        ):
                        assert None == self.log ('done', 'debug')
                        self.handle_close ()
                        
        def pns_multiplex (self, model):
                handlers = self.pns_subscribed.get (model[3])
                if handlers:
                        for handler in handlers:
                                handler (model)
                        
        def pns_signal (self, resolved, model):
                assert None == self.log (netstring.encode (model))
                if model[4] == '_' or model[4].startswith ('.'):
                        return False

                return True
                
        def pns_noise (self, model):
                assert None == self.log (
                        netstring.encode (model), 'noise'
                        )

        #
        # This implementation allows several articulators to "speak-over",
        # each other, to share a PNS/TCP client session together without
        # confusion for them and for the PNS peer. It means that simple
        # redudant statements or less obvious overlapping dialogs won't
        # stampeded the peer or stumble in each other's footsteps. That is
        # a requirement to multiplex independant articulators that may
        # cross each other's path as they walk the peer's semantic graph
        # up and down in all directions.
        #
        # For a simple client, it's a nice one ;-)


if __name__ == '__main__':
        import sys, time, exceptions
        from allegra import loginfo, async_loop
        loginfo.log (
                'Allegra PNS/TCP Client'
                ' - Copyright 2005 Laurent A.V. Szyster | Copyleft GPL 2.0',
                'info'
                ) 

        class PNS_pipe (PNS_client_channel):
                
                def __init__ (self, addr, pipe):
                        self.pns_start = time.time ()
                        self.pns_pipe = pipe
                        PNS_client_channel.__init__ (self)
                        self.tcp_connect (addr)
                        
                def pns_peer (self, ip):
                        if ip:
                                encoded = '%d:%s,0:,0:,0:,' % (len (ip), ip)
                                loginfo.log (encoded)
                                self.pns_articulate ()
                                return
                                
                        assert None == self.log (
                                'close'
                                ' sent="%d" received="%d" seconds="%f"' % (
                                        self.pns_sent, self.pns_received,
                                        time.time () - self.pns_start
                                        ), 'debug'
                                )
                        
                def pns_articulate (self):
                        try:
                                encoded = self.pns_pipe.next ()
                                
                        except exceptions.StopIteration:
                                # no more statements to handle, close
                                self.async_net_push (('0:,0:,0:,0:,',))
                                # self.close_when_done ()
                                return

                        model = list (netstring.decode (encoded))
                        if '' == model[0]:
                                if '' == model[1] == model[2]:
                                        self.pns_quit (model[3])
                                else:
                                        self.pns_command (tuple (model[:3]))
                        elif '' == model[1] and model[0] == model[3]:
                                if model[2]:
                                        self.pns_join (model[3], model[2])
                                else:
                                        self.pns_subscribe (model[3])
                        else:
                                self.pns_statement (
                                        tuple (model[:3]), model[3]
                                        )
                                
                def pns_signal (self, resolved, model):
                        # dump a netstring to STDOUT
                        encoded = netstring.encode (model)
                        loginfo.log (encoded)
                        # waits for the echo to finalize and articulate the
                        # next statement, nicely as the peer sends its echo
                        if model[4].startswith ('.'):
                                self.pns_articulate ()
                                return False
                
                        # _, ! or ? are simply dropped unless they occur
                        # before ., ...
                        return True

                def pns_noise (self, model):
                        # dump a netstring to STDERR
                        loginfo.log (
                                netstring.encode (model), 'noise'
                                )
                        
        if len (sys.argv) > 1:
                if len (sys.argv) > 2:
                        addr = tuple (sys.argv[1:2])
                else:
                        addr = (sys.argv[1], 3534)
        else:
                addr = ('127.0.0.1', 3534)
        PNS_pipe (addr, netstring.netpipe (
                lambda: sys.stdin.read (4096)
                ))
        async_loop.loop ()
        #
        # Allegra PNS/TCP Client
        #
        # The reference implementation of a PNS/TCP pipe, it is one usefull
        # module to develop PNS user agents, but also a nice command line
        # tool to feed and query the peer.
        #
        # As a pipe it reads from STDIN a sequence of netstrings and pipes 
        # them to a PNS/TCP session, then writes relevant statements coming
        # back from the peer to STDOUT and drops the irrelevant statements
        # to STDERR. Example:
        #
        #    python pns_client.py < session.pns 1> signal 2> noise
        #
        # you may also pass the IP address of the PNS peer
        #
        #    python pns_client.py 192.168.1.1 < session.pns 1> signal 2> noise
        #
        # if instructed to close when done, this client will close and delete
        # itself when not more channel is subscribed, and when no more command
        # or statements responses are pending. It is a gracefull pipe and
        # present a trivial interface.


# About This Implementation
#
# This module provides the primary interface level on which to develop
# PNS/TCP user agents. A PNS_client instance allows to multiplex safely
# statements made by independant articulators. 
#
# The length of the sources for this asynchronous PNS/TCP multiplexer 
# show how simple the implementation of PNS actually is.
#
# A simple practical articulator is included in the module. It is a
# synchronous pipe (over a pipelined asynchronous channel!) of 
# PNS statements between a PNS peer and the filesystem. 
#
# The data structure are simple:
#       
#        pns_client.pns_subscribed = {
#                'c': [pns_handler, ...],
#                ...
#                }
#        pns_client.pns_commands = {
#                ('s','p','o'): [pns_handler, ...],
#                ...
#                }
#        pns_client.pns_contexts = {
#                'c': {('s','p','o'): [pns_handler, ...]}, 
#                ...
#                }
#
# An accessor register a handler for a statement, by calling the method:
#
#        pns_client.pns_statement ((s,p,o), n='', pns_handler=None)
#
# which pushes the statement if it there are no handlers registered yet, and
# registers the one passed by the accessor. the handler is defined as
#
#        pns_handler ((s,p,o), [s,p,o,c,d])
#
# and returns True when the handler can be removed from the client hash, 
# False if it expects more. 
#
# This interface allows to develop both "speakers", "listeners" and
# "articulators". The speaker interface is the simplified:
#
#        pns_client.pns_statement ((s,p,o), n='', handler=None)
#
# Listeners and articulators can set watches on a set of statements, without
# confusion or redudant statements.
#
# Protocol statements are handled likewise, by articulators such as: a 
# sentinel for a private context, a subscription manager, etc ... The
# point is that PNS/TCP is simple to implement for diverse applications ;-)
#
# Specifically for its default user agent: simple threaded database logging 
# subscription multiplexers. One PNS/TCP session can manage a single set of
# contexts, possibly a user context, but also provide complete access to the
# persistent store and semantic graph. The fact that PNS/TCP is so flat makes
# it simple to implement fully.
#
#