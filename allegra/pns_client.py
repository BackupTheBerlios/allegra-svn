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

from allegra.tcp_client import TCP_client_channel
from allegra.netstring import \
        Netstring_collector, netstrings_encode, netstrings_decode


class PNS_client_channel (TCP_client_channel, Netstring_collector):
        
        # a PNS client to implement multiplexing user agents like a resolver.
        
        pns_sent = pns_received = 0
        pns_close_when_done = False
        
        def __init__ (self, ip='127.0.0.1', port=3534):
                self.pns_commands = {}
                self.pns_contexts = {}
                TCP_client_channel.__init__ (self, (ip, port))
                Netstring_collector.__init__ (self)
                
        def __repr__ (self):
                return '<pns-client/>'

        def close (self):
                # callback all pending statement handlers with echo, command
                # or peer ip handlers with void responses, then callback
                #
                for context, statements in self.pns_contexts.items ():
                        for resolved, handlers in statements.items ():
                                model = list (resolved)
                                model.append (context)
                                model.append ('.')
                                for handler in handlers:
                                        handler (resolved, model)
                self.pns_contexts = None
                for resolved, handlers in self.pns_commands.items ():
                        model = list (resolved)
                        model.append ('')
                        model.append ('_')
                        for handler in handlers:
                                handler (resolved, model)
                self.pns_commands = None
                self.pns_peer ('')
                TCP_client_channel.close (self)

        collect_incoming_data = Netstring_collector.collect_incoming_data 
        found_terminator = Netstring_collector.found_terminator 

        def netstring_collector_error (self):
                assert None == self.log ('<netstring-error/>', '')
                self.close ()
                
        def netstring_collector_continue (self, encoded):
                if encoded.startswith ('0:,'):
                        assert None == self.log (
                                '<peer-close/>'
                                '<![CDATA[%s]]]!>' % encoded, ''
                                )
                        self.close ()
                        return
                  
                model = netstrings_decode (encoded)
                if len (model) < 5:
                        assert None == self.log (
                                '<invalid-peer-statement/>'
                                '<![CDATA[%s]]]!>' % encoded, ''
                                )
                        self.close ()
                        return
                        
                self.pns_peer (model[0])
                self.netstring_collector_continue = self.pns_continue

        def pns_statement (self, model, context='', handler=None):
                # check for handlers
                # self.log ('%r, %r' % (model, context), '')
                if model[0] == '':
                        # commands
                        handlers = self.pns_commands.setdefault (
                                model, []
                                )
                else:
                        # other statements
                        handlers = self.pns_contexts.setdefault (
                                context, {}
                                ).setdefault (model, [])
                # register a handler
                handlers.append (handler or self.pns_signal)
                if len (handlers) == 1:
                        # send the statement if it is not redundant
                        encoded = netstrings_encode (model)
                        if context:
                                encoded += '%d:%s,' % (len (context), context)
                        else:
                                encoded += '0:,'
                        self.push ('%d:%s,' % (len (encoded), encoded))
                        self.pns_sent += 1
                        return True
                        
                return False

        def pns_continue (self, encoded):
                # Note that there is no validation of the PNS statements
                # because they are trusted to be valid. A client *may*
                # validate, the peer *must* anyway.
                # 
                self.pns_received += 1
                if encoded.startswith ('0:,0:,0:,'):
                        assert None == self.log (
                                '<peer-close/>'
                                '<![CDATA[%s]]]!>' % encoded, ''
                                )
                        self.close ()
                        return
                  
                model = netstrings_decode (encoded)
                if len (model) != 5:
                        assert None == self.log (
                                '<invalid-peer-statement/>'
                                '<![CDATA[%s]]]!>' % encoded, ''
                                )
                        # self.close ()
                        return
                        
                self.pns_log (model)
                resolved = tuple (model[:3])
                if model[0] == '':
                        # commands
                        handlers = self.pns_commands.get (resolved)
                        if handlers == None:
                                assert None == self.log (
                                        '<unsollicited-command-response/>'
                                        '<![CDATA[%s]]>' % encoded, ''
                                        )
                                self.close ()
                                return

                        self.pns_commands[resolved] = [
                                h for h in handlers if h (resolved, model)
                                ]
                        if len (self.pns_commands[resolved]) == 0:
                                del self.pns_commands[resolved]
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
                        len (self.pns_contexts) == 0
                        ):
                        assert None == self.log ('<done/>', '')
                        self.close ()
                        
        def pns_peer (self, ip):
                assert None == self.log (
                        '<peer ip="%s"/>' % ip, ''
                        )
                        
        def pns_log (self, model):
                assert None == self.log (netstrings_encode (model))

        def pns_signal (self, resolved, model):
                # waits for echo
                assert None == self.log (
                        '<signal><![CDATA[%s]]></signal>'
                        '' % netstrings_encode (model), ''
                        )
                if model[4].startswith ('.'):
                        assert None == self.log (
                                '<resolve><![CDATA[%s]]></resolve>'
                                '' % netstrings_encode (resolved), ''
                                )
                        return False

                assert None == self.log (
                        '<pass><![CDATA[%s]]></pass>'
                        '' % netstrings_encode (resolved), ''
                        )
                return True
                
        def pns_noise (self, model):
                assert None == self.log (
                        '<noise><![CDATA[%s]]></noise>'
                        '' % netstrings_encode (model), ''
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

"""
class PNS_multiplexer (PNS_client_channel):
        
        def __init__ (self, ip='127.0.0.1', port=3534):
                PNS_client_channel.__init__ (ip, port)
                self.pns_pipelined = []
                self.pns_peer ('')

        def pns_peer (self, ip):
                if ip == '':
                        # closed
                        for context, multiplex in self.pns_context.items ():
                                for multiplexed in multiplex:
                                        multiplexed.pns_client = None
                        self.pns_contexts = {}
                        self.tcp_connect ()
                        self.pns_statement = self.pns_pipeline
                else:
                        # opened
                        for model, context, handler in self.pns_pipelined:
                                self.pns_client.pns_statement (
                                        model, context, handler
                                        )
                        self.pns_pipelined = None
                        self.pns_pipeline = self.pns_statement
                                
        def pns_pipeline (self, *args):
                self.pns_pipelined.append (args)
                                
        def pns_multiplex (self, context, multiplexed):
                self.pns_contexts.setdefault (
                        context, []
                        ).append (mutliplexed)
                
        def pns_log (self, model):
                multiplex = self.pns_contexts.get (model[3])
                if multiplex:
                        for multiplexed in multiplex:
                                multiplexed.pns_log (tuple (model))
"""


if __name__ == '__main__':
        import sys, time
        assert None == sys.stderr.write (
                'Allegra PNS/TCP Client'
                ' - Copyright 2005 Laurent A.V. Szyster'
                ' | Copyleft GPL 2.0\n'
                ) 
        from exceptions import StopIteration
        from allegra.netstring import netstrings_generator
        
        class PNS_pipe (PNS_client_channel):
                
                def __init__ (self, ip, pipe):
                        self.pns_start = time.time ()
                        self.pns_pipe = pipe
                        PNS_client_channel.__init__ (self, ip)
                        self.tcp_connect ()
                        
                def pns_peer (self, ip):
                        if ip:
                                encoded = '%d:%s,0:,0:,0:,' % (len (ip), ip)
                                sys.stdout.write ('%d:%s,' % (
                                        len (encoded), encoded
                                        ))
                                self.pns_articulate ()
                                return
                                
                        assert None == self.log (
                                '<close sent="%d" received="%d" seconds="%f"'
                                '/>' % (
                                        self.pns_sent, self.pns_received,
                                        time.time () - self.pns_start
                                        ), ''
                                )
                        
                def pns_articulate (self):
                        try:
                                encoded = self.pns_pipe.next ()
                                
                        except StopIteration:
                                # no more statements to handle, close
                                self.push ('12:0:,0:,0:,0:,,')
                                self.close_when_done ()
                                return

                        model = netstrings_decode (encoded)
                        self.pns_statement (
                                tuple (model[:3]), model[3]
                                )
                                
                def pns_log (self, model):
                        pass # we log allready in signal and noise ...

                def pns_signal (self, resolved, model):
                        # dump a netstring to STDOUT
                        encoded = netstrings_encode (model)
                        sys.stdout.write ('%d:%s,' % (len (encoded), encoded))
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
                        encoded = netstrings_encode (model)
                        sys.stderr.write ('%d:%s,' % (len (encoded), encoded))
                        
        if len (sys.argv) > 1:
                ip = sys.argv[1]
        else:
                ip = '127.0.0.1'
        PNS_pipe (ip, netstrings_generator (lambda: sys.stdin.read (4096)))
        from allegra import async_loop
        try:
                async_loop.loop ()
        except:
                async_loop.loginfo.loginfo_traceback ()
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
#        pns_client.pns_commands = {
#                ('s','p','o'): [pns_handler, ...],
#                ...
#                }
#        pns_client.pns_contexts = {
#                'n': {('s','p','o'): [pns_handler, ...]}, 
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