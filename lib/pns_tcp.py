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

import socket

from allegra import netstring, async_net, async_server, public_rdf


def pns_statement (self, encoded):
        if encoded.startswith ('0:,0:,0:,0:,'):
                # user agent closing
                self.log ('pns-user-close', 'info')
                self.handle_close ()
                return
                
        model, error = public_rdf.pns_quatuor (
                encoded, self.pns_subscribed
                )
        if model == None:
                # invalid PNS model, log an error
                self.pns_error (encoded, error)
        elif '' == model[0]:
                if model[1] or model[2]:
                        # open command: index, context or route 
                        model.append ('%s:%d' % self.addr)
                        self.pns_peer.pns_inference.pns_command (model)
                elif model[3] in self.pns_subscribed:
                        # protocol command: unsubscribe
                        self.pns_subscribed.remove (model[3])
                        self.pns_peer.pns_unsubscribe (
                                self, model[3]
                                )
                        self.pns_tcp_continue (model, '.')
                else:
                        self.pns_error (
                                encoded, '7 not subscribed'
                                )
        elif '' == model[1] and model[0] == model[3]:
                if model[2]:
                        # protocol answer: join
                        self.pns_join (model[0], model[2])
                elif model[0] in self.pns_subscribed:
                        self.pns_error (
                                encoded, '8 allready subscribed'
                                )
                else:
                        # protocol question: subscribe
                        self.pns_subscribed.append (model[0])
                        self.pns_peer.pns_subscribe (
                                self, model[0]
                                )
                        self.pns_tcp_continue (model, '.')
        elif '' == model[3]:
                model.append ('%s:%d' % self.addr)
                if model[2]:
                        # infer a context for an open answer ...
                        self.pns_peer.pns_inference.pns_statement (model)
                else:
                        # resolve an open question ...
                        self.pns_peer.pns_resolution.pns_tcp_anonymous (model)
        else:
                # resolve contextual statement ...
                model.append ('%s:%d' % self.addr)
                self.pns_peer.pns_resolution.pns_tcp_statement (model)


class Dispatcher (async_net.Dispatcher):
	
	def __init__ (self):
                async_net.Dispatcher.__init__ (self)
		self.pns_subscribed = []

	def __repr__ (self):
		return 'session id="%x"' % id (self)
                
        async_net_continue = pns_statement

	def pns_error (self, encoded, error):
		encoded = '%s%d:.%s,' % (encoded, len (error)+1, error)
		self.log (encoded, 'pns-error')
		self.async_net_push ((encoded,))
		#
		# self.close_when_done ()
		# PNS/TCP does tolerate non-compliant articulator that
		# produce invalid public names or statements.
        
	def pns_join (name, left):
		# handle a protocol answer, join if not joined or joining.
		circle = self.pns_peer.pns_subscribed.get (name)
		if circle:
			if not (circle.pns_left and circle.pns_right):
				circle.pns_join (left)
		#
		# TODO: move to pns_peer.pns_udp.pns_join and make sure ... ?

	def pns_tcp_continue (self, model, direction):
		self.async_net_push ((
			public_rdf.pns_quintet (model, direction),
			))


class Listen (async_server.Listen):
        
        def __init__ (
                self, pns_peer, ip, 
                precision=3.0, max=5, family=socket.AF_INET
                ):
                self.pns_peer = pns_peer
                async_server.Listen.__init__ (
                        self, Dispatcher, (ip, 3534), 
                        precision, max, family 
                        )

        def __repr__ (self):
                return 'pns-tcp'

        def handle_close (self):
                self.pns_peer.pns_tcp_finalize ()
                self.pns_peer = None
                async_server.Listen.handle_close (self)

        # set the accepted channel's peer; add it to the peer's hash
        # of channels; and push the PNS/TCP server greetings to the client

        def server_accept (self, conn, addr, name):
                dispatcher = async_server.Listen.server_accept (
                        self, conn, addr, name
                        )
                dispatcher.pns_peer = self.pns_peer
                self.pns_peer.pns_sessions['%s:%d' % addr] = dispatcher
                dispatcher.pns_tcp_continue (
                        ('', '', '', self.pns_peer.pns_name), '_'
                        )
                return dispatcher

        # remove the channel from the peer's hash table and unsubscribe
        # all the closed channel's subscriptions, and finally break the
        # circular reference between the channel and the peer.

        def server_close (self, dispatcher):
                del self.pns_peer.pns_sessions['%s:%d' % dispatcher.addr]
                for name in dispatcher.pns_subscribed:
                        self.pns_peer.pns_unsubscribe (self, name)
                dispatcher.pns_peer = None
                async_server.Listen.server_close (self, dispatcher)
