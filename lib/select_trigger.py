# Copyright 1996 by Sam Rushing
#
#                         All Rights Reserved
#
# Permission to use, copy, modify, and distribute this software and
# its documentation for any purpose and without fee is hereby
# granted, provided that the above copyright notice appear in all
# copies and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of Sam
# Rushing not be used in advertising or publicity pertaining to
# distribution of the software without specific, written prior
# permission.
#
# SAM RUSHING DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
# INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS, IN
# NO EVENT SHALL SAM RUSHING BE LIABLE FOR ANY SPECIAL, INDIRECT OR
# CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
# OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
# NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.


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

"http://laurentszyster.be/blog/select_trigger/"

import sys, os, socket, thread

from allegra import (
	netstring, prompt, loginfo, async_loop, finalization, async_core
        )


if os.name == 'posix':

	class Trigger (async_core.Async_file):

		"Thunk back safely from threads into the asynchronous loop"
		
		def __init__ (self):
			self.select_triggers = 0
			r, w = os.pipe ()
			self.trigger = w
			async_core.Async_file.__init__ (self, r)
			self.lock = thread.allocate_lock ()
			self.thunks = []
			assert None == self.log ('open', 'debug')

		def __repr__ (self):
			return 'trigger id="%x"' % id (self)

		def __call__ (self, thunk):
                        "acquire the trigger's lock, thunk and pull"
                        self.lock.acquire ()
			try:
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
                        try:
			        self.recv (8192)
                        except socket.error:
                                return
                        
                        self.lock.acquire ()
			try:
				thunks = self.thunks
				self.thunks = []
			finally:
				self.lock.release ()
			for thunk in thunks:
				try:
					thunk[0] (*thunk[1])
				except:
					self.loginfo_traceback ()
				
                def handle_close (self):
                        assert self.select_triggers == 0
                        self.close ()
                        self.trigger.close ()
                        assert None == self.log ('close', 'debug')
                                
elif os.name == 'nt':

	# win32-safe version

	class Trigger (async_core.Dispatcher):
                
                "Thunk back safely from threads into the asynchronous loop"

		def __init__ (self):
			self.select_triggers = 0
                        #
                        # tricky: get a pair of connected sockets
                        #
			a = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
			w = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
			a.bind (('127.9.9.9', 19999))
			a.listen (1)
			w.setblocking (0)
			try:
				w.connect (('127.9.9.9', 19999))
			except:
				pass
			r, addr = a.accept ()
			a.close ()
			w.setblocking (1)
			self.trigger = w
                        #
			async_core.Dispatcher.__init__ (self, r)
			self.lock = thread.allocate_lock ()
			self.thunks = []
			assert None == self.log ('open', 'debug')

		def __repr__ (self):
			return 'trigger id="%x"' % id (self)

		def __call__ (self, thunk):
                        "acquire the trigger's lock, thunk and pull"
                        self.lock.acquire ()
			try:
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
                        try:
                                self.recv (8192)
                        except socket.error:
                                return
                        
                        self.lock.acquire ()
			try:
				thunks = self.thunks
				self.thunks = []
			finally:
				self.lock.release ()
			for thunk in thunks:
				try:
					thunk[0] (*thunk[1])
				except:
					self.loginfo_traceback ()

                def handle_close (self):
                        assert self.select_triggers == 0
                        self.close ()
                        self.trigger.close ()
                        assert None == self.log ('close', 'debug')

else:
	raise ImportError ('OS "%s" not supported, sorry :-(' % os.name)


class Select_trigger (loginfo.Loginfo, finalization.Finalization):
	
	"""A base class that implements the select_trigger interface
	
		select_trigger ((function, args))
	
	to thunk function and method calls from one thread into the main
	asynchronous loop. Select_trigger implements thread-safe and
	practical loginfo interfaces:
		
		select_trigger_log (data, info=None)
		
	to log information, and
		
		select_trigger_traceback ()
		
	to log traceback asynchronously from a distinct thread."""

	select_trigger = None

	def __init__ (self):
		"""open a Trigger for the Select_trigger class if none has
		been yet and increase the Tigger reference count by one"""
		if self.select_trigger == None:
			Select_trigger.select_trigger = Trigger ()
		self.select_trigger.select_triggers += 1
		
	def __repr__ (self):
		return 'select-trigger id="%x"' % id (self)
		
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
                trigger = self.select_trigger
		trigger.select_triggers -= 1
		if trigger.select_triggers == 0:
			trigger ((trigger.handle_close, ()))
			Select_trigger.select_trigger = None
		self.select_trigger = None