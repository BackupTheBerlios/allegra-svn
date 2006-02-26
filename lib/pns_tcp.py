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

from allegra import netstring, async_net, tcp_server, pns_model


class PNS_session (async_net.Async_net):
	
	def __init__ (self, conn):
		self.pns_subscribed = []
		async_net.Async_net.__init__ (self, conn)

	def __repr__ (self):
		return 'session id="%x"' % id (self)

	def async_net_continue (self, encoded):
		if encoded.startswith ('0:,0:,0:,0:,'):
			# user agent closing
			self.log ('pns-user-close', 'info')
			self.handle_close ()
			return
			
		model, error = pns_model.pns_quatuor (
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
			pns_model.pns_quintet (model, direction),
			))


def pns_tcp_accept (server, channel):
	assert None == channel.log ('pns-tcp-accept', 'debug')
	#
	# set the accepted channel's peer; add it to the peer's hash
	# of channels; and push the PNS/TCP server greetings to the client
	#
	channel.pns_peer = server.pns_peer
	server.pns_peer.pns_sessions['%s:%d' % channel.addr] = channel
	channel.pns_tcp_continue (
		(server.pns_peer.pns_name, '', '', ''), '_'
		)


def pns_tcp_close (channel):
	assert None == channel.log ('pns-tcp-close', 'debug')
	#
	# remove the channel from the peer's hash table and unsubscribe
	# all the closed channel's subscriptions, and finally break the
	# circular reference between the channel and the peer.
	#
	del channel.pns_peer.pns_sessions['%s:%d' % channel.addr]
	for name in channel.pns_subscribed:
		channel.pns_peer.pns_unsubscribe (channel, name)
	channel.pns_peer = None


def pns_tcp_stop (server):
	assert None == server.log ('pns-tcp-stopped', 'debug')
	#
	# close the server once all its channels have been closed,
	# let the PNS peer handle that event and finally break the 
	# circular reference between the server and the peer.
	#
	server.pns_peer.pns_tcp_finalize ()
	server.pns_peer = None
	

# The TCP peer listening on 127.0.0.1, the simplest case.
	
class PNS_TCP_peer (tcp_server.TCP_server_limit):

	TCP_SERVER_CHANNEL = PNS_session

        tcp_server_clients_limit = 256 # ? find out about select/poll limit
	tcp_server_timeout = 3600 # one hour timeout for inactive client
	tcp_server_precision = 60 # one minute precision for defered

	def __init__ (self, pns_peer, ip):
		self.pns_peer = pns_peer
		tcp_server.TCP_server_limit.__init__ (self, (ip, 3534))

	def __repr__ (self):
		return 'pns-tcp'

	tcp_server_accept = pns_tcp_accept

	def tcp_server_close (self, channel):
		pns_tcp_close (channel)
		tcp_server.TCP_server_limit.tcp_server_close (self, channel)

	tcp_server_stop = pns_tcp_stop


# The TCP server listening on another address than the UDP peer
	
class PNS_TCP_server (tcp_server.TCP_server_limit):

	TCP_SERVER_CHANNEL = PNS_session
	
        tcp_server_clients_limit = 1 # a decent limit ;-)
	tcp_server_timeout = 30 # thirty seconds timeout for inactive client
	tcp_server_precision = 3 # one seconds precision for defered

	def __repr__ (self):
		return 'pns-tcp'

	tcp_server_accept = pns_tcp_accept

	def tcp_server_close (self, channel):
		pns_tcp_close (channel)
		tcp_server.TCP_server_limit.tcp_server_close (self, channel)

	tcp_server_stop = pns_tcp_stop


# The Public PNS/TCP Proxy, the seeds of the network, things people can
# run to give public access to the network, complete with throttling for
# TCP and a strict limit of one session per IP address. This is what will
# resist best to DDoS (as well as success for its host ;-)

class PNS_TCP_seed_session (PNS_session):

	def async_net_continue (self, encoded):
		if (
			encoded.startswith ('0:,') and
			not encoded.endswith ('0:,')
			):
			# block commands and any contextual statement,
			# just close (without reporting the abuse to the
			# abuser, there is obviously no need for that ;-)
			#
			self.pns_error ('...')
			return
			
		# process anonymous statement "normally"
		PNS_session.async_net_continue (self, encoded)
		#
		# PNS/TCP public/private seeds are usefull for simplistic
		# user agents without access to PNS/UDP
		#
		# the reason for not allowing commands and contextual
		# statements from seed PNS/TCP user agents is to prevent
		# corruption of the peer's context map and index but also
		# inspection of its semantic graph. a public PNS/TCP service
		# must be safe for public use and only act as a filtering
		# proxy for disabled Internet peers that have no access to
		# the PNS/UDP network. The intended use of a PNS/TCP seed
		# is to filter public PNS feeds for a set of subscribed
		# PNS/UDP contexts and provide access to the service
		# persistent store as well as its subscription services.
		# But not to walk its semantic graph or make contextual
		# statements with authority.
		

class PNS_TCP_seed (tcp_server.TCP_server_throttle):

	TCP_SERVER_CHANNEL = PNS_TCP_seed_session

        tcp_server_clients_limit = 1 # one connection per IP address
	tcp_server_timeout = 6 # minimal timeout for inactive sessions
	tcp_server_precision = 3 # checked evey three seconds, quite fuzzy

	def __init__ (self, pns_peer, ip):
		self.pns_peer = pns_peer
		tcp_server.TCP_server_throttle.__init__ (self, (ip, 3534))

	def __repr__ (self):
		return 'pns-tcp'

	tcp_server_accept = pns_tcp_accept

	def tcp_server_close (self, channel):
		pns_tcp_close (channel)
		tcp_server.TCP_server_throttle.tcp_server_close (
			self, channel
			)
		
	tcp_server_stop = pns_tcp_stop

