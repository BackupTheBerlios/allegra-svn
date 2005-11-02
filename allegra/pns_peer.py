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

"PNS Reference Implementation"

from allegra import \
	netstring, loginfo, async_loop, \
	pns_resolution, pns_inference, pns_tcp, pns_udp


class PNS_peer (async_loop.loginfo.Loginfo):
	
        def __init__ (self, udp_ip, tcp_ip, root):
        	self.pns_root = root
		self.pns_name = udp_ip
		self.pns_sessions = {}
		self.pns_subscribed = {}
		self.pns_subscriptions = {}
		self.pns_resolution = pns_resolution.PNS_resolution (self)
		self.pns_inference = pns_inference.PNS_inference (self)
		if tcp_ip.startswith ('127.'):
			self.pns_tcp = pns_tcp.PNS_TCP_peer (self, tcp_ip)
		elif (
			tcp_ip.startswith ('192.168.') or
			tcp_ip.startswith ('10.')
			):
			self.pns_tcp = pns_tcp.PNS_TCP_server (self, tcp_ip)
		else:
			self.pns_tcp = pns_tcp.PNS_TCP_seed (self, tcp_ip)
		self.pns_udp = pns_udp.PNS_UDP_peer (self, self.pns_name)
			
	def __repr__ (self):
		return '<pns-peer/>'
		
	def pns_subscribe (self, subscriber, name):
		# subscribe to a PNS/UDP circle, and start one if necessary
		assert None == subscriber.log (
			'<subscribe/>'
			'<![CDATA[%s]]!>' % name, ''
			)
		if not self.pns_subscribed.has_key (name):
			self.pns_subscribed[
				name
				] = new = self.pns_udp.pns_subscribe (name)
			self.pns_subscriptions[name] = new.pns_subscribers
		self.pns_subscriptions[name].append (subscriber)

	def pns_unsubscribe (self, subscriber, name):
		# unsubscribe from a PNS/UDP circle, quit one if needs be
		assert None == subscriber.log (
			'<unsubscribe/>'
			'<![CDATA[%s]]!>' % name, ''
			)
		self.pns_subscriptions[name].remove (subscriber)
		if not self.pns_subscriptions[name]:
			self.pns_subscribed[name].pns_quit ()
			del self.pns_subscriptions[name]
			del self.pns_subscribed[name]

	def pns_statement_continue (self, model):
		if self.pns_subscribed.has_key (model[3]):
			# named PNS/TCP statements for a subscribed context
			# are relayed to PNS/UDP or routed ... 
			#
			self.pns_subscribed [
				model[3]
				].pns_statement (model)
		else:
			# named dissent with no matching subscription is
			# indexed and mapped, but not relayed nor routed.
			#
			self.pns_inference.pns_map (model)
			self.pns_tcp_continue (model, '.')
				
	def pns_tcp_continue (self, model, direction):
		# send back an echo to the session user only, either from
		# persistence or semantic, not knowing the state of the
		# PNS/TCP session.
		#
		session = model[4]
		if self.pns_sessions.has_key (session):
			self.pns_sessions [
				session
				].pns_tcp_continue (model, direction)
		#
		# TODO: log the "journal" here to STDOUT
			
	def pns_join_continue (self, name, left):
		if self.pns_subscribed.has_key (name):
			self.pns_subscribed [name].pns_join (left)
				
	def pns_pirp_continue (self, name, encoded, addr):
		# send back the response and log a PIRP statement to stdout
		self.pns_udp.sendto (encoded, addr)
		self.log (netstring.netstrings_encode ((
			name, '', addr[0]
			)))
		#
		# the purpose of logging those statements is to feed back
		# seeds with the addresses of peers trying to join at the
		# seed, providing them with a "point de rendez-vous", a
		# meeting point.
		#
		# 	python pns_peer.py 1> "python pns_client.py"
		#
			
	# error conditions

	def pns_tcp_finalize (self):
		assert None == self.log ('<tcp-finalize/>', '')
		self.pns_shutdown ()

	def pns_udp_finalize (self):
		assert None == self.log ('<udp-finalize/>', '')
		self.pns_udp = pns_udp.PNS_UDP_peer (self, self.pns_name)
		
	def pns_resolution_finalize (self):
		self.pns_resolution = pns_resolution.PNS_resolution (self)
		
	def pns_inference_finalize (self):
		self.pns_inference = pns_inference.PNS_inference (self)
		
	def pns_shutdown (self):
		assert None == self.log ('<shutdown/>', '')
		self.pns_tcp_finalize = self.pns_udp.pns_quit
		self.pns_udp_finalize = self.pns_inference.thread_loop_stop
		self.pns_inference_finalize = \
			self.pns_resolution.thread_loop_stop
		self.pns_resolution_finalize = self.pns_finalize
		self.pns_tcp.tcp_server_stop ()
	
	def pns_finalize (self):
		self.pns_tcp_finalize = self.pns_tcp = None
		self.pns_udp_finalize = self.pns_udp = None
		self.pns_inference_finalize = self.pns_inference = None
		self.pns_resolution_finalize = self.pns_resolution = None
		
	# some debugging utilities

	def pns_resolution_reload (self):
		# a usefull method to reload the persistence code at will
		# from the debugging prompt. simply call it twice if the
		# thread queue is allready stopped.
		#
		if self.pns_resolution_finalize == \
			self.pns_resolution_reload:
			# ... then reload the module and create a new
			# instance of PNS_resolution.
			reload (pns_resolution)
			self.pns_resolution = \
				pns_resolution.PNS_resolution (self)
			del self.pns_resolution_finalize
		else:
			# first, set this method as continuation for persistence
			# and stop the persistence thread queue ...
			self.pns_resolution_finalize = \
				self.pns_resolution_reload
			self.pns_resolution.thread_loop_stop ()
			
	def pns_inference_reload (self):
		# idem for the semantic router.
		if self.pns_inference_finalize == self.pns_inference_reload:
			reload (pns_inference)
			self.pns_inference = pns_inference.PNS_inference (self)
			del self.pns_inference_finalize
		else:
			self.pns_inference_finalize = self.pns_inference_reload
			self.pns_inference.thread_loop_stop ()

	# no need to do the same for PNS/TCP or PNS/UDP, simply because they
	# are bound to the networks and it would be a too damn thing to
	# replace all sessions and circles in-place without breaking their
	# states. so a restart is needed for network debugging.
	#
	# however, PNS/TCP is quite straigthforward and PNS/UDP has it own
	# stub ;-)
	

if __name__ == '__main__':
	loginfo.log (
		'Allegra PNS Peer'
		' - Copyright 2005 Laurent A.V. Szyster'
		' | Copyleft GPL 2.0', 'info'
		)
	import sys
	if '-d' in sys.argv:
		sys.argv.remove ('-d')
		from allegra import sync_stdio
		class PNS_run (PNS_peer):
			def __init__ (self, udp, tcp, root):
				self.python_prompt = sync_stdio.Python_prompt (
					{'pns_peer': self}
					)
				self.python_prompt.start ()
				PNS_peer.__init__ (self, udp, tcp, root)
			def pns_exit (self):
				self.python_prompt.async_stdio_stop ()
				self.python_prompt = None
	elif __debug__:
		class PNS_run (PNS_peer):
			def __init__ (self, udp, tcp, root):
				self.async_catch = async_loop.async_catch
				async_loop.async_catch = self.pns_shutdown
				PNS_peer.__init__ (self, udp, tcp, root)
			def pns_shutdown (self):
				PNS_peer.pns_shutdown (self)
				async_loop.async_catch = self.async_catch
				self.async_catch = None
				return 1
	else:
		from allegra import sync_stdio
		class PNS_run (PNS_peer):
			def __init__ (self, udp, tcp, root):
				self.log ('start', 'info')
				self.sync_stdoe = sync_stdio.Sync_stdoe ()
				self.sync_stdoe.start ()
				self.async_catch = async_loop.async_catch
				async_loop.async_catch = self.pns_shutdown
				PNS_peer.__init__ (self, udp, tcp, root)
			def pns_shutdown (self):
				self.log ('shutdown', 'info')
				PNS_peer.pns_shutdown (self)
				async_loop.async_catch = self.async_catch
				self.async_catch = None
				return 1
			def pns_finalize (self):
				self.log ('stopped', 'info')
				PNS_peer.pns_finalize (self)
				self.sync_stdoe.async_stdio_stop ()
				self.sync_stdoe = None
	if len (sys.argv) > 3:
		PNS_run (sys.argv[1], sys.argv[2], sys.argv[3])
	elif len (sys.argv) > 2:
		PNS_run (sys.argv[1], sys.argv[2], './pns')
	elif len (sys.argv) > 1:
		PNS_run (sys.argv[1], '127.0.0.1', './pns')
	else:
		import socket
		PNS_run (
			socket.gethostbyname (socket.gethostname ()),
			'127.0.0.1', './pns'
			)
	async_loop.loop ()