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

import threading

from allegra.fifo import FIFO_big, FIFO_trunk
from allegra.select_trigger import Select_trigger


class Protected_queue:

        "a wrapper for a FIFO queue accessed from thread-safe a loop"

	def __init__ (self, queue=None):
		self.queue = queue or FIFO_big ()
		self.mon = threading.RLock ()
		self.cv = threading.Condition (self.mon)

	def __len__ (self):
		try:
			self.cv.acquire ()
			l = len (self.queue)
		finally:
			self.cv.release ()
		return l

	def __repr__ (self):
		try:
			self.cv.acquire ()
			r = ''.join (['%r' % i for i in self.queue])
		finally:
			self.cv.release ()
		return '<protected-queue/>' + r
	
	def push (self, item):
		"acquire the lock, push an item at the end the queue and notify"
		try:
			self.cv.acquire ()
			self.queue.push (item)
			self.cv.notify ()
		finally:
			self.cv.release ()
                        
        __call__ = push

	def push_front (self, item):
		"push an item of items in front of the queue"
		try:
			self.cv.acquire ()
			self.queue.push_front (item)
			self.cv.notify ()
		finally:
			self.cv.release ()

	def trunk (self):
		try:
			self.cv.acquire ()
			self.queue = FIFO_trunk ()
		finally:
			self.cv.release ()

	def pop (self):
		"wait for a first item in the queue and pop it"
		try:
			self.cv.acquire ()
			while not self.queue:
				self.cv.wait ()
			item = self.queue.pop ()
		finally:
			self.cv.release ()
		return item


class Thread_loop (threading.Thread, Select_trigger):

        "a thread loop, with thread-safe asynchronous logging"

	def __init__ (self, queue=None):
		self.thread_loop_queue = queue or Protected_queue ()
		Select_trigger.__init__ (self)
		threading.Thread.__init__ (self)
		self.setDaemon (1)

	def __repr__ (self):
		return '<thread-loop id="%x" queued="%d"/>' % (
			id (self), len (self.thread_loop_queue)
			)

	def run (self):
		if self.thread_loop_init ():
			while 1:
				callable = self.thread_loop_queue.pop ()
				if callable == None:
					break

				try:
					callable ()
				except:
					if self.thread_loop_exception ():
                                                break
                                        
		self.thread_loop_delete ()
		if len (self.thread_loop_queue) > 0:
			assert None == self.log (
				'<trunk/><![CDATA[%r]]!'
                                '>' % self.thread_loop_queue, ''
				)
			self.thread_loop_queue.trunk ()
		#
		# ... continue with the Select_trigger.finalization, unless there
		# are circular references for this instance, caveat!

	def thread_loop_init (self):
		assert None == self.log ('<thread-loop-start/>', '')
		return 1
                
        def thread_loop_exception (self):
                self.loginfo_traceback ()
                return 1

        def thread_loop_delete (self):
                assert None == self.log ('<thread-loop-stop/>', '')

        def thread_loop (self, queued):
                self.thread_loop_queue.push (queued)

	def thread_loop_trunk (self):
		self.thread_loop_queue.trunk ()

	def thread_loop_stop (self):
		self.thread_loop_queue.push (None)
