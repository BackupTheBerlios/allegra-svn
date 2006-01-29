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

from allegra import async_chat, loginfo


class Limited_collector (object):
        
        collector_is_simple = True
        
        def __init__ (self, buffer):
                self.data = ''
                self.buffer = buffer

        def collect_incoming_data (self, data):
                if not (0 < self.buffer < len (data)):
                        self.data += data

        def found_terminator (self):
                return True
                

class Loginfo_collector (object):
	
	# collect data to loginfo
	
	collector_is_simple = True

	def __init__ (self, info=None):
		self.info = info
	
	def collect_incoming_data (self, data):
		loginfo.log (data, self.info)
		
	def found_terminator (self):
		return False # final!
		

class Null_collector (object):

	# collect data to /dev/null

	collector_is_simple = True

	def collect_incoming_data (self, data):
		return

	def found_terminator (self):
		return True


class Simple_collector (object):

	# wraps a complex collector with a simple interface
	
	collector_is_simple = True
	
	simple_collector = None

	def __init__ (self, collector):
		collector.set_terminator = self.set_terminator
		collector.get_terminator = self.get_terminator
		self.collector = collector
		self.terminator = None
		self.ac_in_buffer = ''

	def get_terminator (self):
		return self.terminator

	def set_terminator (self, terminator):
		self.terminator = terminator

	def collect_incoming_data (self, data):
                self.ac_in_buffer = self.ac_in_buffer + data
                while async_chat.collect (self.collector):
                        pass
			
	def found_terminator (self):
		return True # allways final
	

class Length_collector (object):

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
	

class Block_decoder (object):
        
        # collect fixed size blocks to decode (like Base64), for instance:
        #
        #         Block_collector (collector, 20, base64.b64decode)
        
        collector_is_simple = True
        
        def __init__ (self, collector, block, decode):
                self.collector = collector
                self.block = block
                self.decode = decode
                self.buffer = ''
        
        def collect_incoming_data (self, data):
                if self.buffer:
                        tail = (len (self.buffer) + len (data)) % self.block
                        if tail:
                                self.buffer = data[-tail:]
                                self.collector.collect_incoming_data (
                                        self.decode (
                                                self.buffer + data[:-tail]
                                                )
                                        )
                        else:
                                self.collector.collect_incoming_data (
                                        self.decode (self.buffer + data)
                                        )
                else:
                        tail = len (data) % self.block
                        if tail:
                                self.buffer = data[-tail:]
                                self.collector.collect_incoming_data (
                                        self.decode (data[:-tail])
                                        )
                        else:
                                self.collector.collect_incoming_data (
                                        decode (data)
                                        )
        
        def found_terminator (self):
                if self.buffer:
                        self.collector.collect_incoming_data (
                                decode (self.buffer)
                                )
                        self.buffer = ''
                return self.collector.found_terminator ()