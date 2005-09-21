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

from asynchat import find_prefix_at_end


class Simple_collector:

	"wraps a complex collector with a simple interface"
	
	# usefull to parse MIME multi-part collected as chunks, but may be
	# used to wrap other complex collector with a simple interface ...
	#
	# this *is* the reference implementation of asynchat's collector
	# interface, copied from its handle_read method. it is the first
	# obvious candidate for a C implementation of Allegra's collectors.

	collector_is_simple = 1
	simple_collector = None

	def __init__ (self, collector):
		self.simple_collector_buffer = ''
		collector.set_terminator = self.set_terminator
		collector.get_terminator = self.get_terminator
		self.terminator = None

	def get_terminator (self):
		return self.terminator

	def set_terminator (self, terminator):
		self.terminator = terminator

	def collect_incoming_data (self, data):
		# copied from the asynchat.async_chat.handle_read and modified
		# to loop through the whole data buffer.
		#
		if self.simple_collector_buffer:
			data = self.simple_collector_buffer + data
			self.simple_collector_buffer = ''
			
		collector = self.simple_collector
		while data:
			lb = len (data)
			terminator = collector.get_terminator ()
			if terminator == None:
				collector.collect_incoming_data (data)
				return

			elif type (terminator) == type (0):
				n = terminator
				if lb < n:
					collector.collect_incoming_data (data)
					self.terminator -= lb
					return
				
				else:
					collector.collect_incoming_data (data[:n])
					data = data[n:]
					self.terminator = 0
					collector.found_terminator ()
			else:
				index = data.find (terminator)
				if index != -1:
					if index > 0:
						collector.collect_incoming_data (
							data[:index]
							)
					data = data[index+len (terminator):]
					collector.found_terminator ()
				else:
					index = find_prefix_at_end (data, terminator)
					if index:
						if index != lb:
							collector.collect_incoming_data (
								data[:-index]
								)
						self.simple_collector_buffer = data[-index:]
					else:
						collector.collect_incoming_data (data)
					return

	def found_terminator (self):
		return 1 # allways final
	

class Length_collector:

	collector_is_simple = 0

	def __init__ (self, collector, size):
		self.set_terminator = collector.set_terminator
		self.length_collector = collector
		self.length_collector_left = size

	def length_collector_truncate (self, data):
		pass # drop any truncated data

	def collect_incoming_data (self, data):
		self.length_left -= len (data)
		if self.length_left < 0:
			self.length_collector.collect_incoming_data (
				data[:self.length_left]
				)
			self.collector_length_truncate (
				data[self.length_left:]
				)
			self.collect_incoming_data = self.length_collector_truncate
		else:
			self.length_collector.collect_incoming_data (data)

	def found_terminator (self):
		if (
			self.length_collector.found_terminator () and
			self.length_collector_left > 0
			):
			self.set_terminator (self.length_collector_left)
		return self.length_collector_left == 0
	

class String_collector:

	"collect data as one string"

	def __init__ (self):
		self.string_collector = []
		self.collect_incoming_data = self.string_collector.append

	def found_terminator (self):
		self.string_collector = ''.join (self.string_collector)
		return 1
	

class Null_collector:

	"collect to /dev/null"

	collector_is_simple = 1

	def collect_incoming_data (self, data):
		pass

	def found_terminator (self):
		return 1


"""
allegra/collectors.py

the Collector interface is nothing new, it is simply an excerp of
the Medusa asynchat.async_chat interface:

	collect_incoming_data (data)
	found_terminator ()
	set_terminator (terminator)
	get_terminator ()

I though it deserved a module of its own, with null, string, file and
length collectors. I also added one property to the interface:

	collector_is_simple = 0 | 1

and a Simple_collector implementation. the Simple_collector wraps
around collectors that use their set_terminator interface. it is
usefull to chain complex collectors together (like Chunked and
Multipart for chunked HTTP file uploads for instance)

using collectors, an application can process data as it comes with
optimal buffering and without blocking. suppose for instance that you
want to scan attachements of incoming mails or need to check digital
signatures of S/MIME envelopes. if you were to collect the whole data
and _then_ process it all, you will more quickly run out of memory for
buffers and the overall performance will drop fast under high load
unless you thread. asynchronous processing collectors can help to make
non-blocking peers that conserve memory and can deliver high
availability, even under very high load.

see the mime_collectors.py module for mime, chunked, multipart, form data,
escaping, but also http and mail (smtp/pop) collectors.

"""