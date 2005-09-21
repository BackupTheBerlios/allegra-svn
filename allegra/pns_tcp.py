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

from allegra.netstring import netstrings_decode, Netstring_collector
from allegra.pns_model import pns_quatuor, pns_tcp_model


class PNS_session (Netstring_collector):
	
	def __init__ (self):
		self.pns_subscribed = []
		Netstring_collector.__init__ (self)

	def __repr__ (self):
		return '<session id="%x"/>' % id (self)

	def netstring_collector_error (self):
		assert None == self.log ('<netstring-error/>', '')
		self.close ()
		#
		# just close if netstring encoding is wrong, do not even
		# bother to send back an error message
		
	def netstring_collector_continue (self, encoded):
		if encoded.startswith ('0:,0:,0:,'):
			# user agent closing gracefully, close too
			assert None == self.log (
				'<pns-user-close/>'
				'<![CDATA[%s]]>' % encoded, ''
				)
			self.close ()
			return
			
		model, error = pns_quatuor (encoded, self.pns_subscribed)
		if model == None:
			# invalid PNS model, log an error
			self.pns_error (encoded, error)
			return
			
		if '' == model[0]:
			# user command, add the sessions text reference and
			# pass to the PNS/Semantic ...
			#
			model.append ('%s:%d' % self.addr)
			self.pns_peer.pns_semantic.pns_command (model)
			return
			
		if '' == model[3]:
			if '' == model[1]:
				# contextless protocol statements, manage
				# the session's subscriptions.
				#
				if model[2]:
					self.pns_join (model[0], model[2])
				elif model[0] in self.pns_subscribed:
					self.pns_subscribed.remove (model[0])
					self.pns_peer.pns_unsubscribe (
						self, model[0]
						)
				else:
					self.pns_subscribed.append (model[0])
					self.pns_peer.pns_subscribe (
						self, model[0]
						)
				self.pns_tcp_continue (model, '.')
				return
				
			# anonymous statement
			model.append ('%s:%d' % self.addr)
			if model[2]:
				# infer a route for an anonymous answers
				self.pns_peer.pns_semantic.pns_statement (
					model
					)
				return

			# resolve anonymous question ...
			self.pns_peer.pns_persistence.thread_loop (
				lambda p=self.pns_peer.pns_persistence,
				m=model:
				p.pns_anonymous (m)
				)
			return

		# resolve named question or answer ...
		#
		model.append ('%s:%d' % self.addr)
		self.pns_peer.pns_persistence.thread_loop (
			lambda p=self.pns_peer.pns_persistence,
			m=model:
			p.pns_statement (m)
			)
			
	def pns_error (self, encoded, error):
		# PNS/TCP does support non-compliant articulator that
		# produce invalid public names or statements.
		#
		encoded = '%s%d:.%s,' % (encoded, len (error)+1, error)
		assert None == self.log (
			'<model-error/><![CDATA[%r]]>' % encoded, ''
			)
		self.push ('%d:%s,' % (len (encoded), encoded))
		# self.close_when_done ()
        
	def pns_join (name, left):
		# handle a protocol answer, join if not joined or joining.
		circle = self.pns_peer.pns_subscribed.get (name)
		if circle:
			if not (circle.pns_left and circle.pns_right):
				circle.pns_join (left)
		#
		# TODO: move to pns_peer.pns_udp.pns_join and make sure ... ?

	def pns_tcp_accept (self, pns_peer):
		assert None == self.log ('<pns-tcp-accept/>', '')
		pns_peer.pns_sessions['%s:%d' % self.addr] = self
		self.pns_peer = pns_peer
		self.pns_tcp_continue (
			(pns_peer.pns_name, '', '', ''), '_'
			)

	def pns_tcp_continue (self, model, direction):
		self.push (pns_tcp_model (model, direction))

	def pns_tcp_close (self):
		assert None == self.log ('<pns-tcp-close/>', '')
		del self.pns_peer.pns_sessions['%s:%d' % self.addr]
		for name in self.pns_subscribed:
			self.pns_peer.pns_unsubscribe (self, name)
		self.pns_peer = None


# The TCP peer listening on 127.0.0.1
	
from allegra.tcp_server import TCP_server_channel, TCP_server

class PNS_TCP_channel (TCP_server_channel, PNS_session):

	def __init__ (self, conn, addr):
		PNS_session.__init__ (self)
		TCP_server_channel.__init__ (self, conn, addr)

	__repr__ = PNS_session.__repr__
	
	found_terminator = Netstring_collector.found_terminator
	collect_incoming_data = Netstring_collector.collect_incoming_data
	
class PNS_TCP_peer (TCP_server):

	TCP_SERVER_CHANNEL = PNS_TCP_channel

        tcp_server_clients_limit = 128	# ? find out about select/poll limit
        tcp_server_precision = 0

	def __init__ (self, pns_peer, ip):
		self.pns_peer = pns_peer
		TCP_server.__init__ (self, (ip, 3534))

	def __repr__ (self):
		return '<tcp/>'

	def tcp_server_accept (self, conn, addr):
		channel = TCP_server.tcp_server_accept (self, conn, addr)
		if not channel:
			return

		channel.pns_tcp_accept (self.pns_peer)
		return channel

	def tcp_server_close (self, channel):
		channel.pns_tcp_close ()
		TCP_server.tcp_server_close (self, channel)

	def tcp_server_finalize (self):
		self.close ()
		self.pns_peer.pns_tcp_finalize ()
		del self.pns_peer


# The TCP server listening on another address than the UDP peer
	
from allegra.tcp_server import TCP_server_limit

class PNS_TCP_limit (TCP_server_limit, PNS_session):

	tcp_inactive_timeout = 3600 # one hour timeout for inactive client
        tcp_server_precision = 600  # checked every ten minutes

	def __init__ (self, conn, addr):
		PNS_session.__init__ (self)
		TCP_server_limit.__init__ (self, conn, addr)

	__repr__ = PNS_session.__repr__
	
	found_terminator = Netstring_collector.found_terminator
	collect_incoming_data = Netstring_collector.collect_incoming_data
	
class PNS_TCP_server (PNS_TCP_peer):

	TCP_SERVER_CHANNEL = PNS_TCP_limit

        tcp_server_clients_limit = 32	# ? find out about select/poll limit
	tcp_server_precision = 6	# six seconds precision for defered


# The Public PNS/TCP Proxy, the seeds of the network, things people can
# run to give public access to the network, complete with throttling for
# TCP and a strict limit of one session per IP address.


from allegra.tcp_server import TCP_server_throttle, TCP_throttler

class PNS_TCP_throttle (TCP_server_throttle, PNS_session):

	tcp_inactive_timeout = 6 # minimal timeout for inactive sessions
	tcp_server_precision = 6 # checked evey six seconds, quite fuzzy

	def __init__ (self, conn, addr):
		PNS_session.__init__ (self)
		TCP_server_throttle.__init__ (self, conn, addr)
	
	__repr__ = PNS_session.__repr__

	found_terminator = Netstring_collector.found_terminator
	collect_incoming_data = Netstring_collector.collect_incoming_data

	def netstring_collector_continue (self, encoded):
		if (
			encoded.startswith ('0:,') and
			not encoded.endswith ('0:,')
			):
			# block commands and any contextual statement,
			# just close (without reporting the abuse to the
			# abuser, there is obviously no need for that ;-)
			#
			self.pns_error ('')
			return
			
		# process anonymous statement "normally"
		PNS_session.netstring_collector_continue (self, encoded)
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
		

class PNS_TCP_seed (TCP_throttler, PNS_TCP_server):

	TCP_SERVER_CHANNEL = PNS_TCP_throttle

        tcp_server_clients_limit = 1	# one connection per IP address
	tcp_server_precision = 3	# three seconds precision for defered

	def __init__ (self, pns_peer, ip):
		self.pns_peer = pns_peer
		TCP_throttler.__init__ (self, (ip, 3534))

	def __repr__ (self):
		return '<tcp-seed/>'

	def tcp_server_accept (self, conn, addr):
		channel = TCP_throttler.tcp_server_accept (self, conn, addr)
		if not channel:
			return
			
		channel.pns_tcp_accept (self.pns_peer)
		return channel

	def tcp_server_close (self, channel):
		channel.pns_tcp_close ()
		TCP_throttler.tcp_server_close (self, channel)
		
	def tcp_server_finalize (self):
		self.close ()
		self.pns_peer.pns_tcp_finalize ()
		del self.pns_peer

