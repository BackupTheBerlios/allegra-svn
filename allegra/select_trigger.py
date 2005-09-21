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

""

import sys
import os
import socket
import thread

from allegra import async_loop
from allegra.loginfo import Loginfo
from allegra.finalization import Finalization


if os.name == 'posix':

	from asyncore import file_dispatcher as File_dispatcher

	class Trigger (File_dispatcher, Loginfo):

		"Wake up a call to select() running in the main thread"
		
		def __init__ (self):
			self.select_triggers = 0
			r, w = os.pipe ()
			self.trigger = w
			File_dispatcher.__init__ (self, r)
			self.lock = thread.allocate_lock ()
			self.thunks = []
			assert None == self.log ('<open/>', '')

		def __repr__ (self):
			return '<select-trigger/>'

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
				for thunk in self.thunks:
					if thunk == None:
						self.handle_close ()
						break
					
					try:
						thunk ()
					except:
						self.loginfo_traceback ()
				self.thunks = []
			finally:
				self.lock.release ()
				
		def handle_close (self):
			self.close ()
			assert None == self.log ('<close/>', '')

elif os.name == 'nt':

	# win32-safe version

	from asyncore import dispatcher as Dispatcher

	class Trigger (Dispatcher, Loginfo):

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

			Dispatcher.__init__ (self, r)
			self.lock = thread.allocate_lock ()
			self.thunks = []
			self._trigger_connected = 0
			assert None == self.log ('<open/>', '')

		def __repr__ (self):
			return '<select-trigger/>'

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
				for thunk in self.thunks:
					if thunk == None:
						self.handle_close ()
						break
					
					try:
						thunk ()
					except:
						self.loginfo_traceback ()
				self.thunks = []
			finally:
				self.lock.release ()

		def handle_close (self):
			self.close ()
			assert None == self.log ('<close/>', '')

else:
	raise ImportError ('OS "%s" not supported, sorry :-(' % os.name)

Trigger.log_info = Trigger.log = Loginfo.log


class Select_trigger (Loginfo, Finalization):

	select_trigger = None

	def __init__ (self):
		if self.select_trigger == None:
			Select_trigger.select_trigger = Trigger ()
		self.select_trigger.select_triggers += 1

	def loginfo_log (self, data, info=None):
		self.select_trigger (
			lambda
			l=self.select_trigger.loginfo_logger,
			d='%r%s' % (self, data),
			i=info:
			l.log (d, i)
			)

	log = loginfo_log
	
	def select_trigger_finalized (self, finalized):
		async_loop.async_finalized.append (
			lambda s=self.select_trigger, f=finalized:
			s (f)
			)

	def finalization (self, finalized):
		self.select_trigger.select_triggers -= 1
		if self.select_trigger.select_triggers == 0:
			self.select_trigger (None)
		self.select_trigger = None
