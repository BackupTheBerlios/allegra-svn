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

import weakref, collections


# The asynchat.py fifo, refactored as "thiner" wrapper and completed

class FIFO_deque:
	
	"FIFO wrapper for a collections.deque instance"
	
	def __init__ (self, list=None):
		self.fifo_deque = collections.deque (list or [])
		self.__len__ = self.fifo_deque.__len__
		self.__getitem__ = self.fifo_deque.__getitem__
		self.pop = self.fifo_deque.popleft
		self.push = self.fifo_deque.append
		self.push_front = self.fifo_deque.appendleft
		
	def __repr__ (self): 
		return '<fifo-deque queued="%d"/>' % len (self)

	def is_empty (self):
		"return True in the FIFO is empty"
		return len (self.fifo_deque) == 0

	def first (self):
		"return the first item in the FIFO"
		return self.fifo_deque[0]


# A variation on the original Output_fifo found in Medusa, refactored to 
# build or merge pipeline's fifo ...

class FIFO_pipeline:
	
	"An embeddable FIFO, usefull to merge diffent fifos into one"
	
	fifo_embedded = None
	
	def __init__ (self, fifo=None):
		self.fifo = fifo or FIFO_deque ()
		self.push = fifo.push

	def __repr__ (self): 
		if self.fifo_embedded == None:
			return '<fifo-pipeline queued="%d"/>' % len (self)
		
		return '<fifo-pipeline embedded="%d"/>' % len (
			self.fifo_embedded
			)

	def __len__ (self):
		"""returns the length of the FIFO queue or the length of
		the current embedded fifo"""
		if self.fifo_embedded == None:
			return len (self.fifo)
		
		return len (self.fifo_embedded)

	def is_empty (self):
		"return True in the FIFO queue is empty"
		return len (self) == 0

	def first (self):
		"return the first item in the FIFO queue"
		if self.fifo_embedded is None:
			return self.fifo.first ()
		
		return self.fifo_embedded.first ()

	def push (self, item):
		self.fifo.push (item)

	def push_fifo (self, fifo):
		"push an embedded fifo in the FIFO queue"
		fifo.fifo_parent = weakref.ref (self)
		self.fifo.push (('FIFO', fifo))

	def push_callable (self, callable):
		"push a callable in the FIFO queue"
		self.fifo.push (('CALL', callable))

	def push_eof (self):
		"push an "
		self.fifo.push (('EOF', None))

	def pop (self):
		if self.fifo_embedded != None:
			return self.fifo_embedded.pop ()
		
		item = self.fifo.pop ()
		self.fifo_embedded = None
		if len (self.fifo) > 0:
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
