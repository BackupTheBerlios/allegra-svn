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

from allegra.netstring import netstrings_encode, netstrings_decode
from allegra.pns_model import pns_name, pns_tcp_model
from allegra.timeouts import Timeouts
from allegra.udp_channel import UDP_dispatcher


def is_ip (name):
	return len ([
		digit for digit in name.split ('.')
		if digit.isdigit () and -1 < int (digit) < 256
		]) == 4

def ip_long (s):
	l = map (long, s.split ('.'))
	i = l.pop (0)
	while l:
		i = (i << 8) + l.pop (0)
	return i

def long_ip (i):
	i, rest = divmod (i, 16777216)
	l = [str (i)]
	i, rest = divmod (rest, 65536)
	l.append (str (i))
	i, rest = divmod (rest, 256)
	l.append (str (i))
	l.append (str (rest))
	return '.'.join (l)


class PNS_circle (UDP_dispatcher):
	
	def __init__ (self, pns_peer, name, subscribers=None):
		self.PNS_SP= '%d:%s,0:,' % (len (name), name)
		self.pns_peer = pns_peer
		self.pns_name = name
		self.pns_sendto_right = pns_peer.pns_udp.sendto
		self.pns_subscribers = subscribers or []
		self.pns_out_of_circle ()

	def __repr__ (self):
		return '<circle name="%s"/>' % self.pns_name

	# asyncore dispatcher's methods 
	
	udp_datagram_size = 1024
			
	def handle_read (self):
		datagram, peer = self.recvfrom ()
		if peer == None:
			assert None == self.log ('<nop/>', '')
			return
			#
			# bogus UDP read event triggered by errors like 
			# ECONNRESET, signaling a "closed" sockets, but
			# only for local peers not routed ones. anyway,
			# this is not an error condition to handle.
			
		if peer != (self.pns_left, 3534):
			assert None == self.log (
				'<wrong-left-peer ip="%s" port="%d"/>' % peer,
				''
				)
			return

		# handle answer from the left peer
		self.pns_answer (datagram, peer)

	def handle_close (self):
		self.pns_peer = self.pns_sendto_right = None
		self.close (self)
		self.pns_quitted ()

	# PNS/TCP continuation

	def pns_tcp_continue (self, model, direction):
		encoded = pns_tcp_model (model, direction)
		for subscriber in self.pns_subscribers:
			subscriber.push (encoded)

	# Events

	def pns_statement (self, model):
		# handle PNS/TCP statements either directly from persistence
		# or not-relayed original statements
		sp = netstrings_encode (model[:2])
		o = self.pns_buffer.get (sp)
		if o != None:
			# buffered statement, TODO: drop or buffer?
			model[2] = o
			return
			
		# not buffered, echo to all subscribers, set timeout and buffer
		self.pns_tcp_continue (model[:4], '.')
		self.pns_peer.pns_udp.timeouts_push (
			(self.pns_right or self.pns_name, sp)
			)
		self.pns_buffer[sp] = model[2]
		if self.pns_left and self.pns_right:
			# joined: record as stated, index and relay
			self.pns_peer.pns_semantic.pns_map (model)
			self.pns_statements[sp] = model[2]
			if model[2]:
				# answer right
				self.pns_sendto_right ('%s%d:%s,' % (
					sp, len (model[2]), model[2]
					), self.pns_right)
				return
					
			# question left
			self.sendto (sp, (self.pns_left, 3534))
			return
				
		# not relayed
		if model[3] == self.pns_name:
			# route named statements that cannot be relayed
			self.pns_peer.pns_semantic.pns_statement (model[:4])
			return
	
	def pns_question (self, datagram, peer):
		# handle in-circle question
		if datagram.startswith ('0:,'):
			# command: quit right
			model = netstrings_decode (datagram)
			if len (model) == 2 and is_ip (model[1]):
				self.pns_quit_right (model[1])
				return

			assert None == self.log (
				'<invalid-protocol-command/>'
				'<![CDATA[%s]]!>' % datagram, ''
				)
			self.pns_quitted ()
			return
			
		if datagram.startswith (self.PNS_SP):
			# protocol question for this circle
			if self.pns_right:
				# in-circle, forward quit and then close
				self.sendto (self.PNS_SP, (
					self.pns_left, 3534
					))
				self.pns_quitted ()
			elif self.pns_left:
				# ? joining
				pass
			else:
				# ? accept
				pass
			return

		# validate question
		model = netstrings_decode (datagram)
		if (
			len (model) != 2 or 
			model[0] != pns_name (model[0])
			):
			assert None == self.log (
				'<invalid-question ip="%s"/>'
				'<![CDATA[%s]]!>' % (peer[0], datagram),
				''
				)
			# TODO: ban IP addresses that send invalid datagrams!
			self.pns_quit ()
			return

		sp = netstrings_encode (model)
		if (
			self.pns_buffer.get (sp) == '' and
			not self.pns_statements.has_key (sp)
			):
			# buffered not stated, drop
			assert None == self.log (
				'<question-drop>'
				'<![CDATA[%s]]!>' % sp, ''
				)
			return
			
		# echo the statement to the PNS/TCP subscribers
		model.append ('')
		model.append (self.pns_name)
		self.pns_tcp_continue (model, '?')
		if self.pns_statements.get (sp) == '':
			# question circled, clear the statement, do not relay
			del self.pns_statements[sp]
			assert None == self.log (
				'<question-circle>'
				'<![CDATA[%s]]!>' % sp, ''
				)
			return

		# relay left
		self.sendto (sp, (self.pns_left, 3534))
		if (
			model[1] == '' and
			self.pns_peer.pns_subscribed.has_key (model[0])
			):
			# protocol question for a subscribed circle, bounce
			# this peer's IP address as the answer.
			left = self.pns_peer.pns_udp.addr[0]
			self.pns_sendto_right (
				'%s%d:%s' % (sp, len(left), left),
				self.pns_right
				)
			return
			
		# pass to persistence
		self.pns_peer.pns_persistence.thread_loop (
			lambda
			m=self.pns_peer.pns_persistence.pns_question,
			q=model:
			m (q)
			) # check persistence ...

	def pns_answer (self, datagram, peer):
		# handle in-circle and out-of-circle answers
		if datagram.startswith ('0:,'):
			if not self.pns_right:
				# out-of-circle
				model = netstrings_decode (datagram)
				if (
					len (model) == 3 and
					model[1] == '' and
					is_ip (model[2])
					):
					# bounce to join left or right of L
					self.pns_join (model[2])
					return
					
			assert None == self.log (
				'<invalid-command-answer/>'
				)
			self.pns_quit ()
			return
				
		if datagram.startswith (self.PNS_SP):
			# handle protocol statement
			model = netstrings_decode (datagram)
			if not (len (model) == 3 and (
				model[2] == '' or is_ip (model[2])
				)):
				assert None == self.log (
					'<invalid-protocol-answer>'
					'<![CDATA[%s]]!>' % sp, ''
					)
				self.pns_quit ()
				return

			if self.pns_right:
				# in-circle, quitted at left!
				return

			# out-of-circle
			if model[2]:
				# accept questions from R
				self.pns_peer.pns_udp.pns_accepted[
					model[2]
					] = self
			else:
				# root join
				self.pns_in_circle (peer)
			return

		# validate answer
		model = netstrings_decode (datagram)
        	if (
        		(len (model[0]) + len (model[1]) + len (
        			'%d%d' % (len (model[0]), len (model[1]))
                        	)) > 512 or
        		model[0] != pns_name (model[0])
        		):
			assert None == self.log (
				'<invalid-question ip="%s"/>'
				'<![CDATA[%s]]!>' % (peer[0], datagram),
				''
				)
			self.pns_quit ()
			return

		sp = netstrings_encode (model[:2])
		if (
			self.pns_buffer.has_key (sp) and
			not self.pns_statements.has_key (sp)
			):
			# buffered not stated, drop
			assert None == self.log (
				'<drop-answer-buffered>'
				'<![CDATA[%s]]!>' % netstrings_encode (model),
				''
				) # ... drop.
			return

		# echo to all subscribers
		model.append (self.pns_name)
		self.pns_tcp_continue (model, '!')
		if self.pns_statements.get (sp) == model[2]:
			# answer circled, clear the statement, do not relay
			del self.pns_statements [sp]
			assert None == self.log (
				'<answer-circle>'
				'<![CDATA[%s]]!>' % sp, ''
				)
			return

		# relay right
		self.pns_sendto_right (
			netstrings_encode (model), self.pns_right
			)
		if (
			model[1] == '' and
			self.pns_peer.pns_subscribed.has_key (model[0])
			):
			# protocol answer, let the named circle handle it
			if self.pns_peer.self.pns_peer.pns_subscribed[
				model[0]
				].pns_protocol_answer (model[2]):
				return
				
		self.pns_peer.pns_persistence.thread_loop (
			lambda
			m=self.pns_peer.pns_persistence.pns_answer,
			q=model:
			m (q)
			) # >>> check persistence ...

	def pns_timeout (self, sp):
		if sp == self.PNS_SP:
			# protocol
			self.pns_tcp_continue ((
				self.pns_name, '', '', self.pns_name
				), '_')
			if self.pns_statements.has_key (sp):
				# timed-out
				o = self.pns_statements.pop (sp)
				if o == '':
					if self.pns_right and self.pns_left:
						# quitted defered until joined
						self.pns_quit ()
					else:
						# quitting
						self.pns_quitted ()
				else:
					pass # joining
			return
				
		if self.pns_buffer.has_key (sp):
			# delete timeouted out buffered subject and predicate
			o = self.pns_buffer[sp]
			del self.pns_buffer[sp]
		else:
			o = ''
		# echo the non-protocol timeouts to all subscribers
		model = netstrings_decode (sp)
		model.append (o)
		model.append (self.pns_name)
		self.pns_tcp_continue (model, '_')
		# quit if timeouts on a statement
		if self.pns_statements.has_key (sp):
			self.pns_quit ()
				
	# States

	def pns_out_of_circle (self):
		assert None == self.log ('<out-of-circle/>', '')
		self.pns_statements = {}
		self.pns_buffer = {}
		self.pns_left = self.pns_right = None
		self.pns_peer.pns_persistence.thread_loop (
			lambda
			p=self.pns_peer,
			n=self.pns_name:
			p.pns_persistence.pns_out_of_circle (n)
			)

	def pns_join (self, left):
		assert None == self.log ('<join ip="%s"/>' % left, '')
		if not self.connected:
			UDP_dispatcher.__init__ (
				self, self.pns_peer.pns_udp.addr[0]
				)
		if self.sendto (self.PNS_SP, (left, 3534)) > 0:
			# joining now
			self.pns_statements[self.PNS_SP] = self.pns_left = left
			self.pns_peer.pns_udp.timeouts_push ((
				self.pns_name, self.PNS_SP
				))
		else:
			# failed to join
			self.pns_left = None
		
	def pns_joined (self, right):
		if self.pns_right:
			# in-circle
			if self.pns_statements.has_key (self.PNS_SP):
				# quitting or joined, bounce (,,R) to I
				assert None == self.log (
					'<joined-bounce-right '
					'ip="%s" port="%d"/>' % right, ''
					)
				if self.pns_sendto_right ('0:,0:,%d:%s,' % (
					len (self.pns_right[0]),
					self.pns_right[0]
					), right) == 0:
					# failed to bounce
					pass
				return
				
			# accepting, send (S,,I) to R and (S,,R) to I as,
			# telling I it is accepted between L and R
			assert None == self.log (
				'<joined-accept '
				'ip="%s" port="%d"/>' % right, ''
				)
			if self.pns_sendto_right (self.PNS_SP + '%d:%s,' % (
				len (self.pns_right[0]), self.pns_right[0]
				), right) == 0:
				# failed to accept I
				pass
			if self.pns_sendto_right (self.PNS_SP + '%d:%s,' % (
				len (right[0]), right[0]
				), self.pns_right) == 0:
				# failed to notice R
				pass
			# I accepted between L and R
			self.pns_peer.pns_udp.pns_accepted[right[0]] = self
			return
			
		if self.pns_left:
			# joining, bounce (,,L) to I
			assert None == self.log (
				'<joined-bounce-left '
				'ip="%s" port="%d"/>' % right, ''
				)
			if self.pns_sendto_right ('0:,0:,%d:%s,' % (
				len (self.pns_left), self.pns_left
				), right) == 0:
				# failed to bounce
				pass
			return
			
		# out-of-circle, send (S,,) to I and join root
		if self.pns_sendto_right (self.PNS_SP + '0:,', right) > 0:
			self.pns_root (right)
		else:
			assert None == self.log (
				'<joined-root-fail '
				'ip="%s" port="%d"/>' % right, ''
				)
			
	def pns_root (self, right):
		# set the L=R, bind a UDP port if joined and set the 
		# state to in-circle
		assert None == self.log ('<root ip="%s"/>' % right[0], '')
		self.pns_left = right[0]
		if not self.connected:
			UDP_dispatcher.__init__ (
				self, self.pns_peer.pns_udp.addr[0]
				)
		self.pns_in_circle (right)

	def pns_in_circle (self, right):
		# set R, register the circle as joined
		assert None == self.log (
			'<in-circle ip="%s" port="%d"/>' % right, ''
			)
		self.pns_right = right
		self.pns_peer.pns_udp.pns_joined[right] = self
		# then check if no protocol statement has been made
		if self.pns_statements.has_key (self.PNS_SP):
			# if quit has been stated, quit now
			if self.pns_statements.pop (self.PNS_SP) == '':
				assert None == self.log (
					'<in-circle-quit '
					'ip="%s" port="%d"/>' % right, ''
					)
				self.pns_quit ()
					
	def pns_quit (self):
		if self.pns_statements.has_key (self.PNS_SP):
			if self.pns_statements[self.PNS_SP]:
				# joining
				assert None == self.log (
					'<quit-joining/>', ''
					)
			else:
				pass # quitting
			return
			
		if not self.pns_right:
			# out-of-circle
			assert None == self.log ('<quit-out-of-cicle/>', '')
			return

		# in-circle, notice subscribers, set a timeout,
		# send (,R) to L and (S,,L) to R, then finally
		# substitutes a new circle to the one subscribed if
		# there are at least one subscriber.
		#
		assert None == self.log ('<quit/>', '')
		self.pns_statements[self.PNS_SP] = ''
		self.pns_peer.pns_udp.timeouts_push (
			(self.pns_right, self.PNS_SP)
			)
		model = (self.pns_name, '', '', self.pns_name)
		self.pns_tcp_continue (model, '!')
		self.pns_tcp_continue (model, '?')
		if self.pns_left != self.pns_right[0]:
			self.sendto ('0:,%d:%s,' % (
				len (self.pns_right[0]),
				self.pns_right[0]
				), (self.pns_left, 3534))
		self.pns_sendto_right (self.PNS_SP + '%d:%s,' % (
			len (self.pns_left), self.pns_left
			), self.pns_right)
		if self.pns_subscribers:
			self.pns_peer.pns_subscribed[
				self.pns_name
				] = self.pns_peer.pns_udp.pns_subscribe (
					self.pns_name,
					self.pns_subscribers
					)
			self.pns_subscribers = []

	def pns_quitted (self):
		if self.pns_right:
			del self.pns_peer.pns_udp.pns_joined[self.pns_right]
			self.pns_right = self.pns_left = None


class PNS_axis (PNS_circle): 

	# An axis is restricted to peers which IP addresses mask its name.
	# Their purpose is to seed the network and let peers connect the grid
	# they decide to build.
	#
	# A peer with IP address 10.0.0.1 will not be allowed to join the axis
	# named 13:192.168.1.255, but the peer 192.168.1.17 will be accepted.
	#
	# There are three kind of axis: Longitude, Latitude and Equator/Pole.
	#
	# A PNS latitude represents an outer edge of the network, usually
	# the peer's network as defined by its IP netmask, for instance:
	#
	#	213.189.175.255
	#
	# PNS longitudes represents the inner edges of the network, usually
	# the peer's IP address and its inversed netmask, for instance:
	#
	#	255.255.245.18
	#
	# The Equator/Pole of PNS, which represents all edges, is named
	#
	#	255.255.255.255
	#
	# and by subscribing to it you allow any peer to join.

	def __init__ (self, pns_peer, name, subscribers):
		self.pns_netmask = ip_long (name)
		PNS_circle.__init__ (self, pns_peer, name, subscribers)

	def __repr__ (self):
		return '<axis name="%s"/>' % self.pns_name
		
	def pns_join (self, left):
		if ip_long (left) & self.pns_netmask == self.pns_netmask:
			PNS_circle.pns_join (self, left)
			return
			
		assert None == self.log (
			'<pns-join-drop ip="%s"/>' % left, ''
			)

	def pns_joined (self, right):
		if ip_long (right[0]) & self.pns_netmask == self.pns_netmask:
			PNS_circle.pns_joined (self, right)
			return

		# TODO: ban ?
		assert None == self.log (
			'<joined-drop ip="%s"/>' % right[0], ''
			)


class PNS_UDP_peer (UDP_dispatcher, Timeouts):

	# PNS/UDP, at 320Kbps may set 80 timeouts per seconds, one every
	# 12,5 millisecond which would amount to 240 timeouts in 3 seconds.
	# If you start scale up to 512KBps for the same circles period of
	# 3 seconds, your timeouts queue may hold up to 768 timeouts and
	# you may set one every 4 milliseconds.
	#
	# Even with a C heapqueue this would drain unnecessarily: a fifo
	# polled every 300 millisecond is precise enough to do the job ;-)
	#
	# Precision is not important, because PNS/TCP clients synchronize
	# with the PNS peer and not their clock and that there is a latency
	# in communication that is variable and tolerated up to 3 seconds.
	#
	# 768 or 3 timeouts the seconds would only require around three
	# defered collections.

	def __init__ (self, pns_peer, ip):
		self.pns_peer = pns_peer
		self.pns_joined = {}
		self.pns_accepted = {}
		Timeouts.__init__ (self, self.pns_timeout, 3, 0.3)
		UDP_dispatcher.__init__ (self, ip, 3534)
		for name in self.pns_peer.pns_subscribed.keys ():
			self.pns_peer.pns_subscribed[
				name
				] = self.pns_subscribe (
					name,
					self.pns_peer.pns_subscriptions[name]
					)

	def __repr__ (self):
		return '<udp/>'

	udp_datagram_size = 512
			
	def handle_read (self):
		datagram, peer = self.recvfrom ()
		if peer == None:
			assert None == self.log ('<nop/>', '')
			return
		
		if self.pns_joined.has_key (peer):
			# in circle question ...
			self.pns_joined[peer].pns_question (datagram, peer)
			return
			
		if self.pns_accepted.has_key (peer[0]):
			# question from a new peer accepted at right
			self.pns_accepted[peer[0]].pns_question (
				datagram, peer
				)
			return

		# out of circle
		model = netstrings_decode (datagram)
		if (
			len (model) != 2 or
			model[0] == '' or
			model[0] != pns_name (model[0])
			):
			# log and drop invalid out-of-circle question ...
			assert None == self.log (
				'<invalid ip="%s"/><![CDATA[%s]]!>' % (
					peer[0], datagram
					), ''
				)
			return

		# if subscribed, joined ...
		if self.pns_peer.pns_subscribed.has_key (model[0]):
			self.pns_peer.pns_subscribed[
				model[0]
				].pns_joined (peer)
			return
			
		# not subscribed, check persistence for a PIRP answer >>>
		if not self.pns_peers.has_key (peer):
			self.pns_peer.pns_persistence.thread_loop (
				lambda
				m=self.pns_peer.pns_persistence.pns_pirp,
				n=model[0], p=peer:
				m (n, p)
				)

	def handle_close (self):
		self.close ()
		for circle in self.pns_joined.values ():
			circle.close ()
		self.timeouts_defer = self.timeouts_stop

	def timeouts_stop (self, when):
		Timeouts.timeouts_stop (self, when)
		self.pns_peer.pns_udp_finalize ()
		del self.pns_peer

	def pns_subscribe (self, name, subscribers=None):
		if is_ip (name):
			return PNS_axis (self.pns_peer, name, subscribers)
			
		return PNS_circle (self.pns_peer, name, subscribers)
		
	def pns_quit (self):
		assert None == self.log ('<quit/>', '')
		for circle in self.pns_joined.values ():
			circle.pns_quit ()
		self.timeouts_push ((None, ''))

	def pns_timeout (self, reference):
		if reference[0] == None:
			if reference[1]:
				pass # ?
			else:
				# closing UDP peer
				self.handle_close ()
		elif self.pns_joined.has_key (reference[0]):
			# in-circle timeout
			self.pns_joined[reference[0]].pns_timeout (
				reference[1]
				)
		elif self.pns_peer.pns_subscribed.has_key (reference[0]):
			# out-of-circle timeout
			self.pns_peer.pns_subscribed[
				reference[0]
				].pns_timeout (reference[1]) 
		else:
			assert None == self.log (
				'<timeout-drop/>'
				'<![CDATA[%s]]!>' % reference[1], ''
				)

# Just PNS/UDP with logging stubs for TCP, Persistence and Semantic.
#
# the fast track for development and implementation of the UDP protocol,
# then also a nice scriptable test automate. each modules should have
# one, but only this one is complex enough to require it.

if __name__ == '__main__':
	import sys
	sys.stderr.write (
		'Allegra PNS/UDP - Copyright 2005 Laurent A.V. Szyster\n'
		)
	from allegra import async_loop
	from allegra.loginfo import Loginfo
	class PNS_persistence (Loginfo):
		def __repr__ (self):
			return '<persistence/>'
		def thread_loop (self, call):
			call ()
		def pns_pirp (self, name, addr):
			assert None == self.log (
				'<pirp ip="%s"/>'
				'<![CDATA[%s]]!>' % (addr[0], name), ''
				)
		def pns_out_of_circle (self, name):
			assert None == self.log (
				'<out-of-circle/><![CDATA[%s]]!>' % name, ''
				)
	class PNS_semantic (Loginfo):
		def __repr__ (self):
			return '<semantic/>'
		def pns_statement (self, model):
			assert None == self.log (
				'<![CDATA[%s]]!'
				'>' % netstrings_encode (model), ''
				)
	class PNS_peer (Loginfo):
		def __init__ (self, udp_ip):
			self.pns_name = udp_ip
			self.pns_sessions = {}
			self.pns_subscribed = {}
			self.pns_subscriptions = {}
			self.pns_persistence = PNS_persistence ()
			self.pns_semantic = PNS_semantic ()
			self.pns_udp = PNS_UDP_peer (self, self.pns_name)
			self.pns_udp_finalize = self.pns_exit
		def __repr__ (self):
			return ''
		def pns_subscribe (self, name):
			# subscribe the peer stub and join
			if not self.pns_subscribed.has_key (name):
				assert None == self.log (
					'<subscribe/>'
					'<![CDATA[%s]]!>' % name, ''
					)
				self.pns_subscribed[
					name
					] = new = self.pns_udp.pns_subscribe (
						name, [self]
						)
				self.pns_subscriptions[
					name
					] = new.pns_subscribers
		def pns_unsubscribe (self, name):
			# unsubscribe the peer stub and quit
			assert None == self.log (
				'<unsubscribe/><![CDATA[%s]]!>' % name, ''
				)
			self.pns_subscriptions[name].remove (self)
			self.pns_subscribed[name].pns_quit ()
			del self.pns_subscriptions[name]
			del self.pns_subscribed[name]
		# log PNS/TCP subscription to stdout! so that the log
		# proper can be saved to a file while debug is echoed
		# to the console or dropped
		push = Loginfo.loginfo_log
		def pns_shutdown (self):
			self.pns_udp.pns_quit ()
		def pns_exit (self):
			assert None == self.log ('<quit/>', '')
	if '-d' in sys.argv:
		sys.argv.remove ('-d')
		from allegra.sync_stdio import Python_prompt
		class PNS_run (PNS_peer):
			def __init__ (self, udp_ip):
				self.python_prompt = Python_prompt (
					{'pns_peer': self}
					)
				self.python_prompt.start ()
				PNS_peer.__init__ (self, udp_ip)
			def pns_exit (self):
				self.python_prompt.async_stdio_stop ()
				self.python_prompt = None
	else:
		PNS_run = PNS_peer
	PNS_run (sys.argv[1])
	try:
		async_loop.loop ()
	except:
		async_loop.loginfo.loginfo_traceback ()
		
# The Longest Modules! PNS/UDP is a nice state machine ;-)
#
# this PNS/UDP implementation comes with a logging stub for the peer's
# interfaces, but it is still the longest library in Allegra. even with a 
# 3bit syntax, PNS/UDP is kind of tricky, much more clockwork than computer
# science or semantic system design.
#
# there are two main issues: how not to disrupt the flow of information
# while conducting the protocol, and how to zip properly simultaneously
# disbanding peers? traffic must be as fluid as possible, because the media
# is allready unreliable. a circle may disband because there is a bandwith
# bottlenecks or a slow peer in it, but it will not really break.

# Notes:
#
# NAT - a PNS/UDP peer can function behind a NAT router, provided that the
#       incoming UDP traffic to port 3534 is forwarded to the PNS peer host
#	
#	pin-through/rendez-vous requires network services, something that
#	is fine for Skype but not for PNS. implementing PNS on a private
#       network requires that traffic must not flow out of it. It's a feature
#       *not* to work-around NAT and to design PNS to fit *in* the router
#       or the firewall.