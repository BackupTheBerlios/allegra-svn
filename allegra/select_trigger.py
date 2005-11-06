# Copyright (C) 2005 Laurent A.V. Szyster
# 
# This library is free software; you can redistribute it and/or modify
# it under the terms of version 2.1 of the GNU Lesser General Public
# License as published by the Free Software Foundation.
# 
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307
# USA

"A practical interface to Sam Rushing's select_trigger implementation"

import sys, os, socket, thread, asyncore

from allegra import netstring, prompt, loginfo, async_loop, finalization


if os.name == 'posix':

	class Trigger (asyncore.file_dispatcher, loginfo.Loginfo):

		"Wake up a call to select() running in the main thread"
		
		def __init__ (self):
			self.select_triggers = 0
			r, w = os.pipe ()
			self.trigger = w
			asyncore.file_dispatcher.__init__ (self, r)
			self.lock = thread.allocate_lock ()
			self.thunks = []
			assert None == self.log ('open', 'debug')

		def __repr__ (self):
			return 'trigger id="%x"' % id (self)

		def __call__ (self, thunk):
			try:
				self.lock.acquire ()
				self.thunks.append (thunk)
			finally:
				self.lock.release ()
			os.write (self.trigger, 'x')

		def readable (self):
			return 1

		def writable (self):
			return 0

		def handle_connect (self):
			pass

		def handle_read (self):
			self.recv (8192)
			try:
				self.lock.acquire ()
				thunks = self.thunks
				self.thunks = []
			finally:
				self.lock.release ()
			for thunk in thunks:
				if thunk == None:
					self.handle_close ()
					break
				
				try:
					thunk[0] (*thunk[1])
				except:
					self.loginfo_traceback ()
				
		def handle_close (self):
			self.close ()
			assert None == self.log ('close', 'debug')

elif os.name == 'nt':

	# win32-safe version

	class Trigger (asyncore.dispatcher, loginfo.Loginfo):

		address = ('127.9.9.9', 19999)

		def __init__ (self):
			self.select_triggers = 0
			a = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
			w = socket.socket (socket.AF_INET, socket.SOCK_STREAM)

			# tricky: get a pair of connected sockets
			a.bind (self.address)
			a.listen (1)
			w.setblocking (0)
			try:
				w.connect (self.address)
			except:
				pass
			r, addr = a.accept ()
			a.close ()
			w.setblocking (1)
			self.trigger = w

			asyncore.dispatcher.__init__ (self, r)
			self.lock = thread.allocate_lock ()
			self.thunks = []
			self._trigger_connected = 0
			assert None == self.log ('open', 'debug')

		def __repr__ (self):
			return 'trigger id="%x"' % id (self)

		def __call__ (self, thunk):
			try:
				self.lock.acquire ()
				self.thunks.append (thunk)
			finally:
				self.lock.release ()
			self.trigger.send ('x')

		def readable (self):
			return 1

		def writable (self):
			return 0

		def handle_connect (self):
			pass

		def handle_read (self):
			self.recv (8192)
			try:
				self.lock.acquire ()
				thunks = self.thunks
				self.thunks = []
			finally:
				self.lock.release ()
			for thunk in thunks:
				if thunk == None:
					self.handle_close ()
					break
				
				try:
					thunk[0] (*thunk[1])
				except:
					self.loginfo_traceback ()

		def handle_close (self):
			self.close ()
			assert None == self.log ('close', 'debug')

else:
	raise ImportError ('OS "%s" not supported, sorry :-(' % os.name)

Trigger.log = Trigger.log_info = loginfo.Loginfo.log
Trigger.select_triggers = 0


class Select_trigger (loginfo.Loginfo, finalization.Finalization):
	
	"""A base class that implements the select_trigger interface
	
		select_trigger((function, args))
	
	to thunk function and method calls from one thread into the main
	asynchronous loop. Select_trigger implements thread-safe and
	practical loginfo interfaces:
		
		select_trigger_log(data, info=None)
		
	to log information, and
		
		select_trigger_traceback(ctb=None)
		
	to log traceback asynchronously from a distinct thread."""

	select_trigger = None

	def __init__ (self):
		"""open a Trigger for the Select_trigger class if none has
		been yet and increase the Tigger reference count by one"""
		if self.select_trigger == None:
			Select_trigger.select_trigger = Trigger ()
		self.select_trigger.select_triggers += 1
		
	def __repr__ (self):
		return 'select-trigger id="%x"' % self (id)
		
	def select_trigger_log (self, data, info=None):
		"thunk a log call to the async loop via the select trigger"
		self.select_trigger ((self.log, (data, info)))
		
	def select_trigger_traceback (self):
		"""return a compact traceback tuple and thunk its log via the
		select_trigger to the async loop."""
		ctb = prompt.compact_traceback ()
		self.select_trigger ((self.loginfo_log, (
			loginfo.compact_traceback_netstrings (ctb), 
			'traceback'
			)))
		return ctb

	def finalization (self, finalized):
		"decrease the Trigger's reference count and close it if zero"
		self.select_trigger.select_triggers -= 1
		if self.select_trigger.select_triggers == 0:
			self.select_trigger (None)
		self.select_trigger = None

	#def select_trigger_finalized (self, finalized):
	#	async_loop.async_finalized.append (
	#		lambda s=self.select_trigger, f=finalized:
	#		s (f)
	#		)

		