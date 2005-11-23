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


class Trunked_deque:
        
        "a deque implementation to trunk protected FIFO queues safely"

        def __len__ (self):
                "return 1, a trunked deque has allways one item" 
                return 1
                
        def __getitem__ (self, index):
                "return None or raise IndexError"
                if index == 0:
                        return None
                        
                raise IndexError, 'trunked FIFO deque'
                
        def append (self, item): 
                "drop any item appended to the deque"
                pass

        def popleft (self): 
                "return None, the closing item for a FIFO consumer"
                return None
        
        pop = popleft
        
        appendleft = append


class Protected_deque:

        "a thread-safe wrapper for a FIFO deque"

	def __init__ (self, queue=None):
		self.deque = collections.deque (queue or [])
		self.mon = threading.RLock ()
		self.cv = threading.Condition (self.mon)

        def __repr__ (self):
                "return a safe netstring representation of the FIFO queue"
                r = []
                try:
                        self.cv.acquire ()
                        l = len (self.deque)
                        for item in self.deque:
                                try:
                                        r.append ('%r' % (item,))
                                except:
                                        r.append (
                                                'item id="%x"' % id (item)
                                                )
                finally:
                        self.cv.release ()
                return netstring.encode ((
                        'protected_deque queued="%d"' % l,
                        netstring.encode (r)
                        ))
        
	def __len__ (self):
                "return the queue's length"
		try:
			self.cv.acquire ()
			l = len (self.deque)
		finally:
			self.cv.release ()
		return l

        def __getitem__ (self, index):
                "return the queue's length"
                try:
                        self.cv.acquire ()
                        return self.deque[index]
                                
                finally:
                        self.cv.release ()
                
        def append (self, item):
                "push an item at the end the queue and notify"
                try:
                        self.cv.acquire ()
                        self.deque.append (item)
                        self.cv.notify ()
                finally:
                        self.cv.release ()
        
        __call__ = append
                
        def popleft (self):
                "wait for a first item in the FIFO queue and pop it"
                try:
                        self.cv.acquire ()
                        while len (self.deque) == 0:
                                self.cv.wait ()
                        item = self.deque.popleft ()
                finally:
                        self.cv.release ()
                return item

        def appendleft (self, item):
                "push an item of items in front of the FIFO queue"
                try:
                        self.cv.acquire ()
                        self.deque.appendleft (item)
                        self.cv.notify ()
                finally:
                        self.cv.release ()

        def pop (self):
                "wait for a last item in the FIFO queue and pop it"
                try:
                        self.cv.acquire ()
                        while len (self.deque) == 0:
                                self.cv.wait ()
                        item = self.deque.pop ()
                finally:
                        self.cv.release ()
                return item

        def trunk (self):
                """Replace the FIFO queue with a trunked deque implementation
                and return the replaced deque instance."""
                try:
                        self.cv.acquire ()
                        trunked = self.deque
                        self.deque = Trunked_deque ()
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
		self.thread_loop_queue = queue or Protected_deque ()
		select_trigger.Select_trigger.__init__ (self)
		threading.Thread.__init__ (self)
		self.setDaemon (1)

	def __repr__ (self):
		return 'thread-loop id="%x"' % id (self)

	def run (self):
                """The Thread Loop
                
                If thread_loop_init() is True call queued instance until
                None is popped or and exception is raised and not catched
                by thread_loop_throw. Finally, if thread_loop_delete() is
                True, trunk the thread loop queue.
                """
		if self.thread_loop_init ():
			while True:
				queued = self.thread_loop_queue.popleft ()
				if queued == None:
					break

				try:
				        queued[0] (*queued[1])
				except:
					if self.thread_loop_throw ():
                                                break
                                        
		if self.thread_loop_delete ():
                        trunked = self.thread_loop_queue.trunk ()
                        if trunked:
                                self.select_trigger_log (
                                        netstring.encode ([
                                                '%r' % (i,) for i in trunked
                                                ]), 'debug'
                                        )
		#
		# ... continue with the Select_trigger.finalization, unless
                # there are circular references for this instance, caveat!

        def thread_loop (self, queued):
                "assert debug log and push a simple callable in the queue"
                assert None == self.log ('%r %r' % queued, 'queued')
                self.thread_loop_queue (queued)

        def thread_loop_stop (self):
                "assert debug log and push the stop item None in the queue"
                assert None == self.log ('stop-when-done', 'debug')
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
