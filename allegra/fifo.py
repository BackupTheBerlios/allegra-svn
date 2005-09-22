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

import weakref


class FIFO_trunk:
	
	"a fifo to trunk protected queues safely"

	def __repr__ (self): return '<fifo-stop/>'

	def __len__ (self): return 0

	def pop (self): return None
	
	def push (self, item): pass

	push_front = push_front_trunk = push


class FIFO_small:
	
	# TODO: use the asyncore fifo instead.

	"FIFO class for small queues, wrapping a simple list"
	
	def __init__ (self, list=None):
		self.fifo_list = list or []
		self.__len__ = self.fifo_list.__len__
		self.__getitem__ = self.fifo_list.__getitem__
		self.push = self.fifo_list.append
		
	def is_empty (self):
		return len (self.fifo_list) == 0

	def first (self):
		return self.fifo_list[0]

	def push_front (self, data):
		self.fifo_list.insert (0, data)

	def pop (self):
		return self.fifo_list.pop (0)


# Sam Rushing's fifo quick translation of scheme48/big/queue.scm
	
class FIFO_big:

	"a fifo class for large queues, implemented with lisp-style pairs."

	def __init__ (self):
		self.head, self.tail = None, None
		self.length = 0
		self.node_cache = None
		
	def __len__ (self):
		return self.length

	def __getitem__ (self, index):
		if (index < 0) or (index >= self.length):
			raise IndexError, "index out of range"
		else:
			if self.node_cache:
				j, h = self.node_cache
				if j == index - 1:
					result = h[0]
					self.node_cache = index, h[1]
					return result
				else:
					return self._nth (index)
			else:
				return self._nth (index)

	def _nth (self, n):
		i = n
		h = self.head
		while i:
			h = h[1]
			i -= 1
		self.node_cache = n, h[1]
		return h[0]

	def is_empty (self):
		return self.length == 0

	def first (self):
		if self.head is None:
			raise ValueError, "first() of an empty queue"
		else:
			return self.head[0]

	def push (self, v):
		self.node_cache = None
		self.length += 1
		p = [v, None]
		if self.head is None:
			self.head = p
		else:
			self.tail[1] = p
		self.tail = p

	def push_front (self, thing):
		self.node_cache = None
		self.length += 1
		old_head = self.head
		new_head = [thing, old_head]
		self.head = new_head
		if old_head is None:
			self.tail = new_head

	def pop (self):
		self.node_cache = None
		pair = self.head
		if pair is None:
			raise ValueError, "pop() from an empty queue"
		else:
			self.length -= 1
			[value, next] = pair
			self.head = next
			if next is None:
				self.tail = None
			return value


class FIFO_pipeline:
	
	"An embeddable FIFO, usefull to merge diffent fifos into one"
	
	def __init__ (self, fifo=None):
		self.fifo = fifo or FIFO_small ()
		self.fifo_embedded = None

	def __len__ (self):
		# returns the length of the embedding fifo or the current embedded
		# fifo, not the accurate length of the Output_fifo
		if self.fifo_embedded is None:
			return len (self.fifo)
		
		return len (self.fifo_embedded)

	def is_empty (self):
		return len (self) == 0

	def first (self):
		if self.fifo_embedded is None:
			return self.fifo.first ()
		
		return self.fifo_embedded.first ()

	def push (self, item):
		self.fifo.push (item)

	def push_fifo (self, fifo):
		fifo.fifo_parent = weakref.ref (self)
		self.fifo.push (('FIFO', fifo))

	def push_callable (self, callable):
		self.fifo.push (('CALL', callable))

	def push_eof (self):
		self.fifo.push (('EOF', None))

	def pop (self):
		if self.fifo_embedded is not None:
			return self.fifo_embedded.pop ()
		
		item = self.fifo.pop ()
		self.fifo_embedded = None
		if len (self.fifo):
			front = self.fifo.first ()
			if type (front) is type (()):
				kind, value = front
				if kind == 'FIFO':
					self.fifo_embedded = value
				elif kind == 'EOF':
					parent = self.fifo_parent ()
					self.fifo_parent = None
					parent.fifo_embedded = None
				elif kind == 'CALL':
					value ()
				self.fifo.pop ()
		return item
