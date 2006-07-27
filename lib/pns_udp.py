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

from allegra import netstring, async_core, timeouts, ip_peer, pns_model


class Circle (async_core.Dispatcher):
                        	
        pns_datagram_size = 1024
                                
	def __init__ (self, pns_peer, name, subscribers=None):
		self.PNS_SP= '%d:%s,0:,' % (len (name), name)
		self.pns_peer = pns_peer
		self.pns_name = name
		self.pns_sendto_right = pns_peer.pns_udp.sendto
		self.pns_subscribers = subscribers or []
		self.pns_out_of_circle ()

	def __repr__ (self):
		return 'circle name="%s"' % self.pns_name

	# asyncore dispatcher's methods 
	
        def writable (self):
                return False
        
	def handle_read (self):
		datagram, peer = self.recvfrom (self.pns_datagram_size)
		if peer == None:
			assert None == self.log ('nop', 'debug')
			return
			#
			# bogus UDP read event triggered by errors like 
			# ECONNRESET, signaling a "closed" sockets, but
			# only for local peers not routed ones. anyway,
			# this is not an error condition to handle.
			
		if peer != (self.pns_left, 3534):
			assert None == self.log (
				'wrong-left-peer ip="%s" port="%d"' % peer,
				'error'
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
		encoded = pns_model.pns_quintet (model, direction)
		for subscriber in self.pns_subscribers:
			subscriber.async_net_push ((encoded,))

	# Events

	def pns_statement (self, model):
		# handle PNS/TCP statements either directly from persistence
		# or not-relayed original statements
		sp = netstring.encode (model[:2])
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
			self.pns_peer.pns_inference.pns_map (model)
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
			self.pns_peer.pns_inference.pns_statement (model[:4])
			return
	
	def pns_question (self, datagram, peer):
		# handle in-circle question
		if datagram.startswith ('0:,'):
			# command: quit right
			model = list (netstring.decode (datagram))
			if len (model) == 2 and ip_peer.is_ip (model[1]):
				self.pns_quit_right (model[1])
				return

			assert None == self.log (
				datagram, 'invalid-protocol-command'
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
		model = list (netstring.decode (datagram))
		if (
			len (model) != 2 or 
			model[0] != pns_model.pns_name (model[0])
			):
			assert None == self.log (
				datagram, 'invalid-question'
				)
			# TODO: ban IP addresses that send invalid datagrams!
			self.pns_quit ()
			return

		sp = netstring.encode (model)
		if (
			self.pns_buffer.get (sp) == '' and
			not self.pns_statements.has_key (sp)
			):
			# buffered not stated, drop
			assert None == self.log (datagram, 'drop')
			return
			
		# echo the statement to the PNS/TCP subscribers
		model.append ('')
		model.append (self.pns_name)
		self.pns_tcp_continue (model, '?')
		if self.pns_statements.get (sp) == '':
			# question circled, clear the statement, do not relay
			del self.pns_statements[sp]
			assert None == self.log (datagram, 'circle')
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
			
		# resolve ...
		self.pns_peer.pns_resolution.pns_udp_question (model)

	def pns_answer (self, datagram, peer):
		# handle in-circle and out-of-circle answers
		if datagram.startswith ('0:,'):
			if not self.pns_right:
				# out-of-circle
				model = list (netstring.decode (datagram))
				if (
					len (model) == 3 and
					model[1] == '' and
					ip_peer.is_ip (model[2])
					):
					# bounce to join left or right of L
					self.pns_join (model[2])
					return
					
			assert None == self.log (
				datagram, 'invalid-command-answer'
				)
			self.pns_quit ()
			return
				
		if datagram.startswith (self.PNS_SP):
			# handle protocol statement
			model = list (netstring.decode (datagram))
			if not (len (model) == 3 and (
				model[2] == '' or ip_peer.is_ip (model[2])
				)):
				assert None == self.log (
					datagram, 'invalid-protocol-answer'
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
		model = list (netstring.decode (datagram))
        	if (
        		(len (model[0]) + len (model[1]) + len (
        			'%d%d' % (len (model[0]), len (model[1]))
                        	)) > 512 or
        		model[0] != pns_model.pns_name (model[0])
        		):
			assert None == self.log (
				datagram, 'invalid-question'
				)
			self.pns_quit ()
			return

		sp = netstring.encode (model[:2])
		if (
			self.pns_buffer.has_key (sp) and
			not self.pns_statements.has_key (sp)
			):
			# buffered not stated, drop
			assert None == self.log (datagram, 'drop')
			return

		# echo to all subscribers
		model.append (self.pns_name)
		self.pns_tcp_continue (model, '!')
		if self.pns_statements.get (sp) == model[2]:
			# answer circled, clear the statement, do not relay
			del self.pns_statements [sp]
			assert None == self.log (datagram, 'circle')
			return

		# relay right
		self.pns_sendto_right (
			netstring.encode (model), self.pns_right
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
				
		# resolve ...
		self.pns_peer.pns_resolution.pns_udp_answer (model)

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
		model = list (netstring.decode (sp))
		model.append (o)
		model.append (self.pns_name)
		self.pns_tcp_continue (model, '_')
		# quit if timeouts on a statement
		if self.pns_statements.has_key (sp):
			self.pns_quit ()
				
	# States

	def pns_out_of_circle (self):
		assert None == self.log ('out-of-circle', 'debug')
		self.pns_statements = {}
		self.pns_buffer = {}
		self.pns_left = self.pns_right = None
		self.pns_peer.pns_resolution.pns_udp_out_of_circle (
			self.pns_name
			)

	def pns_join (self, left):
		assert None == self.log ('join ip="%s"' % left, 'debug')
		if self.socket == None:
			if not ip_peer.udp_bind (
                                self, self.pns_peer.pns_udp.addr[0]
                                ):
                                self.pns_left = None # failed to join
                                return
                                
		if self.sendto (self.PNS_SP, (left, 3534)) > 0:
			# joining now
			self.pns_statements[self.PNS_SP] = self.pns_left = left
			self.pns_peer.pns_udp.timeouts_push ((
				self.pns_name, self.PNS_SP
				))
		else:
			self.pns_left = None # failed to join
		
	def pns_joined (self, right):
		if self.pns_right:
			# in-circle
			if self.pns_statements.has_key (self.PNS_SP):
				# quitting or joined, bounce (,,R) to I
				assert None == self.log (
					'joined-bounce-right'
					' ip="%s" port="%d"/>' % right,
					'debug'
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
				'joined-accept'
				' ip="%s" port="%d"' % right, 'debug'
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
				'joined-bounce-left'
				' ip="%s" port="%d"' % right, 'debug'
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
				'joined-root-fail'
				' ip="%s" port="%d"' % right, 'debug'
				)
			
	def pns_root (self, right):
		# set the L=R, bind a UDP port and move to "in-circle" state
		assert None == self.log ('root ip="%s"' % right[0], 'debug')
		self.pns_left = right[0]
		if self.socket == None:
			ip_peer.udp_bind (
				self, self.pns_peer.pns_udp.addr[0]
				)
		self.pns_in_circle (right)

	def pns_in_circle (self, right):
		# set R, register the circle as joined
		assert None == self.log (
			'in-circle ip="%s" port="%d"' % right, 'debug'
			)
		self.pns_right = right
		self.pns_peer.pns_udp.pns_joined[right] = self
		# then check if no protocol statement has been made
		if self.pns_statements.has_key (self.PNS_SP):
			# if quit has been stated, quit now
			if self.pns_statements.pop (self.PNS_SP) == '':
				assert None == self.log (
					'in-circle-quit'
					' ip="%s" port="%d"' % right, 'debug'
					)
				self.pns_quit ()
					
	def pns_quit (self):
		if self.pns_statements.has_key (self.PNS_SP):
			if self.pns_statements[self.PNS_SP]:
				# joining
				assert None == self.log (
					'quit-joining', 'debug'
					)
			else:
				pass # quitting
			return
			
		if not self.pns_right:
			# out-of-circle
			assert None == self.log ('quit-out-of-cicle', 'debug')
			return

		# in-circle, notice subscribers, set a timeout,
		# send (,R) to L and (S,,L) to R, then finally
		# substitutes a new circle to the one subscribed if
		# there are at least one subscriber.
		#
		assert None == self.log ('quit', 'debug')
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


class Axis (Circle): 

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
		self.pns_netmask = ip_peer.ip_long (name)
		Circle.__init__ (self, pns_peer, name, subscribers)

	def __repr__ (self):
		return 'pns-udp-axis name="%s"' % self.pns_name
		
	def pns_join (self, left):
		if ip_peer.ip_long (
                        left
                        ) & self.pns_netmask == self.pns_netmask:
			Circle.pns_join (self, left)
			return
			
		self.log ('pns-join-drop ip="%s"' % left, 'error')

	def pns_joined (self, right):
		if ip_peer.ip_long (
                        right[0]
                        ) & self.pns_netmask == self.pns_netmask:
			Circle.pns_joined (self, right)
			return

		# TODO: ban ?
		self.log ('joined-drop ip="%s"' % right[0], 'error')


class Peer (async_core.Dispatcher, timeouts.Timeouts):

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
	# Practically, at a sustained 512KBps rated (full speed!), every
	# third of a second, a batch of 256 timeouts is handled, most of
	# which are either simple and fast to handle (remove the timeout
	# entry).

        pns_datagram_size = 512
                        
	def __init__ (self, pns_peer, ip):
		self.pns_peer = pns_peer
		self.pns_joined = {}
		self.pns_accepted = {}
		timeouts.Timeouts.__init__ (self, self.pns_timeout, 3, 0.3)
		if ip_peer.udp_bind (self, ip, 3534):
                        subscribed = pns_peer.pns_subscribed
                        subscriptions = pns_peer.pns_subscriptions
        		for name in subscribed.keys ():
        			subscribed[name] = self.pns_subscribe (
					name, subscriptions[name]
					)
                #
                # keep trying ... but later ;-)

	def __repr__ (self):
		return 'pns-udp'

        def writable (self):
                return False

	def handle_read (self):
		datagram, peer = self.recvfrom (pns_datagram_size)
		if peer == None:
			assert None == self.log ('nop', 'debug')
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
		model = list (netstring.decode (datagram))
		if (
			len (model) != 2 or
			model[0] == '' or
			model[0] != pns_model.pns_name (model[0])
			):
			# log and drop invalid out-of-circle question ...
			self.log (
				'invalid-peer ip="%s"' % peer[0], 'error'
				)
			return

		# if subscribed, joined ...
		if self.pns_peer.pns_subscribed.has_key (model[0]):
			self.pns_peer.pns_subscribed[
				model[0]
				].pns_joined (peer)
			return
			
		# not subscribed, resolve a PIRP answer >>>
		if not self.pns_peers.has_key (peer):
			self.pns_peer.pns_resolution.pns_udp_pirp (
				model[0], peer
				)

	def handle_close (self):
		self.close ()
		for circle in self.pns_joined.values ():
			circle.handle_close ()
		# self.timeouts_continue = self.timeouts_stop

	def timeouts_stop (self):
		self.timeouts_timeout = None
		self.pns_peer.pns_udp_finalize ()
		del self.pns_peer

	def pns_subscribe (self, name, subscribers=None):
		if ip_peer.is_ip (name):
			return Axis (self.pns_peer, name, subscribers)
			
		return Circle (self.pns_peer, name, subscribers)
		
	def pns_quit (self):
		assert None == self.log ('quit', 'debug')
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
				'%s' % reference[1], 'timeout-drop'
				)

# Just PNS/UDP with logging stubs for TCP, Resolution and Inference.
#
# the fast track for development and implementation of the UDP protocol,
# then also a nice scriptable test automate. each modules should have
# one, but only this one is complex enough to require it.

if __name__ == '__main__':
	from allegra import loginfo, async_loop
	loginfo.log (
		'Allegra PNS/UDP'
		' - Copyright 2005 Laurent A.V. Szyster'
		' | Copyleft GPL 2.0', 'info'
		)

	class PNS_resolution (loginfo.Loginfo):

		def __repr__ (self):
			return 'resolution'

		def pns_udp_question (self, model):
			self.log (
				netstring.encode (model), 
				'question'
				)

		def pns_udp_answer (self, model):
			self.log (
				netstring.encode (model), 
				'question'
				)

		def pns_udp_pirp (self, name, addr):
			self.log (netstring.encode ((
				addr[0], name
				)), 'pirp')

		def pns_udp_out_of_circle (self, name):
			self.log (name, 'out-of-circle')

	class PNS_inference (loginfo.Loginfo):

		def __repr__ (self):
			return 'inference'

		def pns_statement (self, model):
			self.log (netstring.encode (model), 'statement')

	class PNS_peer (loginfo.Loginfo):

		def __init__ (self, udp_ip):
			self.pns_name = udp_ip
			self.pns_sessions = {}
			self.pns_subscribed = {}
			self.pns_subscriptions = {}
			self.pns_resolution = PNS_resolution ()
			self.pns_inference = PNS_inference ()
			self.pns_udp = Peer (self, self.pns_name)
			self.pns_udp_finalize = self.pns_exit

		def __repr__ (self):
			return 'pns_peer'

		def pns_subscribe (self, name):
			# subscribe the peer stub and join
			if not self.pns_subscribed.has_key (name):
				self.log (name, 'subscribe')
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
			self.log (name, 'unsubscribe')
			self.pns_subscriptions[name].remove (self)
			self.pns_subscribed[name].pns_quit ()
			del self.pns_subscriptions[name]
			del self.pns_subscribed[name]

		# log PNS/TCP subscription to stdout! so that the log
		# proper can be saved to a file while debug is echoed
		# to the console or dropped
		push = loginfo.Loginfo.loginfo_log

		def pns_shutdown (self):
			self.pns_udp.pns_quit ()

		def pns_exit (self):
			assert None == self.log ('quit', 'debug')

	if '-d' in sys.argv:
		sys.argv.remove ('-d')
		from allegra import sync_stdio
		class PNS_run (PNS_peer):
			def __init__ (self, udp_ip):
				self.python_prompt = sync_stdio.Python_prompt (
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
	async_loop.dispatch ()
		
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