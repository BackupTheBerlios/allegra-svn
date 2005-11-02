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

from allegra.loginfo import Loginfo


class Loginfo_collector (Loginfo):
	
	# collect data to loginfo
	
	collector_is_simple = True

	def __init__ (self, info=None):
		self.loginfo_info = info
	
	def collect_incoming_data (self, data):
		self.log (data, self.loginfo_info)
		
	def found_terminator (self):
		return True # final!
		

class Null_collector:

	# collect data to /dev/null

	collector_is_simple = True

	def collect_incoming_data (self, data):
		return

	def found_terminator (self):
		return True


class Simple_collector:

	# wraps a complex collector with a simple interface
	
	collector_is_simple = True
	
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
				
				collector.collect_incoming_data (data[:n])
				data = data[n:]
				self.terminator = 0
				collector.found_terminator ()
				return
	
			index = data.find (terminator)
			if index != -1:
				if index > 0:
					collector.collect_incoming_data (
						data[:index]
						)
				data = data[index+len (terminator):]
				collector.found_terminator ()
				return
	
			index = find_prefix_at_end (data, terminator)
			if index:
				if index != lb:
					collector.collect_incoming_data (
						data[:-index]
						)
				self.simple_collector_buffer = data[-index:]
			else:
				collector.collect_incoming_data (data)
		#
		# This *is* the reference implementation of asynchat's 
		# collector interface, copied from the asynchat.py's
		# async_chat.handle_read method and modified to loop through 
		# the whole data buffer at once.
		#
		# It is the first obvious candidate for a C implementation of
		# Allegra's collectors.
		
	
	def found_terminator (self):
		return True # allways final
	

class Length_collector:

	# wraps a complex collector with a length collector
	
	collector_is_simple = False

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
			self.collect_incoming_data = \
				self.length_collector_truncate
		else:
			self.length_collector.collect_incoming_data (data)

	def found_terminator (self):
		if (
			self.length_collector.found_terminator () and
			self.length_collector_left > 0
			):
			self.set_terminator (self.length_collector_left)
		return self.length_collector_left == 0
	

class Netstring_collector:
	
	collector_is_simple = False
	
	def __init__ (self):
		self.netstring_collector = ''
		self.set_terminator (':')

	def collect_incoming_data (self, data):
		self.netstring_collector += data

	def found_terminator (self):
		if self.get_terminator () != ':':
			if self.netstring_collector[-1] != ',':
				self.nestring_collector_error ()
				return
				
			self.netstring_collector_continue (
				self.netstring_collector[:-1]
				)
			self.netstring_collector = ''
			self.set_terminator (':')
			return
			
		if self.netstring_collector.isdigit ():
			self.set_terminator (
				int (self.netstring_collector) + 1
				)
			self.netstring_collector = ''
			return

		self.nestring_collector_error ()

	# def nestring_collector_continue (self):
		
	# def nestring_collector_error (self):
		

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

	collector_is_simple = False or True

to signal which collector use their set_terminator interface or leave its
management to their accessor (usually a TCP channel).

The Simple_collector wraps around complex collectors and provide its accessor
with a simple interface. The Length_collector simply allow a complex collector
to simply fed with a given length of data. They are both usefull to chain 
complex collectors together, like Chunked and Multipart for chunked HTTP file 
uploads for instance.


Blurb

Using collectors, an application can process data as it comes with
optimal buffering and without blocking. Suppose for instance that you
want to scan attachements of incoming mails or need to check digital
signatures of S/MIME envelopes. If you were to collect the whole data
and _then_ process it all, you will more quickly run out of memory for
buffers and the overall performance will drop fast under high load
unless you thread. Asynchronous processing collectors can help to make
non-blocking peers that conserve memory and can deliver high
availability, even under very high load.

See the mime_collectors.py module for mime, chunked, multipart, form data,
escaping, but also http and mail (smtp/pop) collectors.

"""