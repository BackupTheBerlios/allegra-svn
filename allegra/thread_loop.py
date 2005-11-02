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

import threading, collections

from allegra import netstring, select_trigger


class deque_trunk:
        
        "a deque implementation to trunk protected FIFO queues safely"

        def __repr__ (self): 
                return '<deque-trunk/>'

        def __len__ (self):
                "a trunked FIFO deque is allways closing, return 1" 
                return 1
                
        def __getitem__ (self, index):
                if index == 1:
                        return None
                        
                raise IndexError, 'trunked FIFO deque'
                
        def pop (self): 
                "return None, the usual end for a FIFO consumer"
                return None
        
        def append (self, item): 
                "drop any item pushed in the FIFO deque"
                pass

        popleft = pop
        
        appendleft = append


class Protected_FIFO:

        "a thread-safe wrapper for a FIFO deque"

	def __init__ (self, queue=None):
		self.fifo_deque = collections.deque (queue or [])
		self.mon = threading.RLock ()
		self.cv = threading.Condition (self.mon)

        def __call__ (self, item):
                "push an item at the end the queue and notify"
                try:
                        self.cv.acquire ()
                        self.fifo_deque.append (item)
                        self.cv.notify ()
                finally:
                        self.cv.release ()
                        
	def __len__ (self):
                "return the queue's length"
		try:
			self.cv.acquire ()
			l = len (self.fifo_deque)
		finally:
			self.cv.release ()
		return l

	def __repr__ (self):
                "return a safe netstring representation of the queue"
                r = []
		try:
			self.cv.acquire ()
                        for item in self.fifo_deque:
                                try:
			                r.append ('%r' % (item,))
                                except:
                                        r.append (
                                                '<item id="%x"/>' % id (item)
                                                )
		finally:
			self.cv.release ()
		return netstring.netstrings_encode ((
                        'protected_queue', netstring.netstrings_encode (r)
                        ))
	
        push = __call__
        
	def push_front (self, item):
		"push an item of items in front of the FIFO queue"
		try:
			self.cv.acquire ()
			self.fifo_deque.appendleft (item)
			self.cv.notify ()
		finally:
			self.cv.release ()

	def pop (self):
		"wait for a first item in the FIFO queue and pop it"
		try:
			self.cv.acquire ()
			while len (self.fifo_deque) == 0:
				self.cv.wait ()
			item = self.fifo_deque.popleft ()
		finally:
			self.cv.release ()
		return item

        def is_empty (self):
                "return True if the FIFO queue is empty"
                try:
                        self.cv.acquire ()
                        result = (len (self.fifo_deque) == 0)
                finally:
                        self.cv.release ()
                return result

        def trunk (self):
                """Replace the FIFO queue with a trunked deque implementation
                and return the replaced deque instance."""
                try:
                        self.cv.acquire ()
                        trunked = self.fifo_deque
                        self.fifo_deque = deque_trunk ()
                finally:
                        self.cv.release ()
                return trunked
                #
                # In effect, trunking implies closing a running thread loop 
                # and dropping any item queued thereafter, which is precisely 
                # The Right Thing To Do when a thread loop queue is stopped: 
                # prevent accessors to push  references that won't be popped 
                # out and leak.                
                

class Thread_loop (threading.Thread, select_trigger.Select_trigger):

        "a thread loop, with thread-safe asynchronous logging"

	def __init__ (self, queue=None):
		self.thread_loop_queue = queue or Protected_FIFO ()
		select_trigger.Select_trigger.__init__ (self)
		threading.Thread.__init__ (self)
		self.setDaemon (1)

	def __repr__ (self):
                """return the 7-bit XML representation:
                        
                        <thread-loop id="%x" queued="%d"/>'
                        
                of the instance."""
		return '<thread-loop id="%x" queued="%d"/>' % (
			id (self), len (self.thread_loop_queue)
			)

	def run (self):
                """The Thread Loop
                
                If thread_loop_init() is True call queued instance until
                None is popped or and exception is raised and not catched
                by thread_loop_throw. Finally, if thread_loop_delete() is
                True, trunk the thread loop queue."""
		if self.thread_loop_init ():
			while True:
				queued = self.thread_loop_queue.pop ()
				if queued == None:
					break

				try:
				        queued[0] (*queued[1])
				except:
					if self.thread_loop_throw ():
                                                break
                                        
		if self.thread_loop_delete ():
                        trunked = [
                                '%r' % (i,)
                                for i in self.thread_loop_queue.trunk ()
                                ]
                        assert None == self.select_trigger_log (
                                netstring.netstrings_encode (trunked),
                                'debug'
                                )
		#
		# ... continue with the Select_trigger.finalization, unless
                # there are circular references for this instance, caveat!

        def thread_loop (self, queued):
                "assert debug log and push a simple callable in the queue"
                assert None == self.log ('%r' % (queued,), 'debug')
                self.thread_loop_queue (queued)

        def thread_loop_stop (self):
                "assert debug log and push the stop item None in the queue"
                assert None == self.log ('stop_when_done', 'debug')
                self.thread_loop_queue (None)

	def thread_loop_init (self):
                "return True, assert a debug log of the thread loop start"
		assert None == self.log ('start', 'debug')
		return True
                
        def thread_loop_throw (self):
                "return False, log a compact traceback via the select trigger"
                self.select_trigger_traceback ()
                return False

        def thread_loop_delete (self):
                "return True, assert a debug log of the thread loop start"
                assert None == self.log ('stop', 'debug')
                return True
