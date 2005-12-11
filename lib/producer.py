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

"A fork of the original Medusa's collection of producers"

import types, exceptions


class Simple_producer (object):
	
	"producer for a string"

	def __init__ (self, data, buffer_size=4096):
		self.data = data
		self.buffer_size = buffer_size

	def more (self):
		if len (self.data) > self.buffer_size:
			result = self.data[:self.buffer_size]
			self.data = self.data[self.buffer_size:]
			return result
		
		else:
			result = self.data
			self.data = ''
			return result

	def content_length (self):
		return len (self.data)

	def producer_stalled (self):
		return False


class Composite_producer (object):
	
	# TODO: fix a bug in this producer, and make it work again!
	
	# This is a more "modern" composite producer than the original
	# one, with support for stalled producers and generators. it is the
	# bread & butter of Allegra's PRESTo! with the Buffer_reactor.
	
        def __init__ (self, head, body, glob=4096):
        	assert (
        		type (head) == types.StringType and 
        		type (body) == types.GeneratorType
        		)
        	self.current = head
                self.generator = body
                self.glob = glob
                
        def more (self):
        	if self.current == '':
        		return ''
        		
        	buffer = ''
        	limit = self.glob
        	while True:
	        	if type (self.current) == types.StringType:
	        		buffer += self.current
	        		try:
	  				self.current = self.generator.next ()
		  		except exceptions.StopIteration:
		  			self.current = ''
		  			break
		  		
		  		if len (buffer) > limit:
		  			break
		  			
			elif self.current.producer_stalled ():
				assert buffer != '' # watch this!
				break
				
			else:
				data = self.current.more ()
				if data:
					buffer += data
					if len (buffer) > limit:
						break
					
					else:
						continue
						
	        		try:
	  				self.current = self.generator.next ()
		  		except exceptions.StopIteration:
		  			self.current = ''
		  			break
		  		
		return buffer
                
	def producer_stalled (self):
		try:
			return self.current.producer_stalled ()
			
		except:
			return False
			
	# Note that this class also makes the original Medusa's lines, buffer 
	# and globbing producer redundant. What this class does it to glob
	# as much strings as possible from a MIME like data structure:
	#
	#	head = 'string'
	#	body = (generator of 'string' or producer ())
	#
	# In effect, if you can generate only strings (like xml_utf.py can)
	# a composite producer will glob more or less precise chunks to fill
	# the accessor's buffer.

class File_producer (object):
	
	"producer wrapper for file[-like] objects"

	def __init__ (self, file, buffer_size=1<<16):
		self.file = file
		self.buffer_size = buffer_size

	def more (self):
		return self.file.read (self.buffer_size)

	def producer_stalled (self):
		return False
	

class Encoding_producer (object):

	"a producer that encodes a UNICODE producer's data in a given charset"

	def __init__ (self, producer, encoding='UTF-8', option='ignore'):
		self.producer = producer
		self.producer_stalled = self.producer.producer_stalled
		self.encoding = encoding
		self.option = option

	def more (self):
		return self.producer.more ().encode (
			self.encoding, self.option
			)

# Composite Producer
#
# The composite producer let its accessor mix strings and producers
# at will, to compose the message body, preceded by a single string
# for the head. Taking a generator for the body parts, instanciation
# of the composing strings and producers may take place at the last
# moment, when bandwith is available for the consumer.
# 
# Finally, note that the producer "globs" strings until a producer
# is found, producing an "optimal" stream by reducing the number
# of calls to send but without blocking on stalled producers. Globbing
# a la Medusa made sense for serving large static files to many slow
# clients, it is a lot less usefull when serving small dynamic responses
# to a limited set of collaborating user agents.
#
# The typical use of the Composite producer is to traverse a flat
# sequence of strings and producers. Null strings and producers
# will simply be passed trough, until more data is available or the
# end of the body is reached.
#
# Or, if you prefer, you can "print" strings or producers to a
# composite producer, and it will do "the right thing". 
#
# It is a practical "porte-manteaux" structure to assemble and
# serialize appropriately things like MIME messages, XML strings
# and cryptographic signatures together. Using it with care can
# produce fast *and* reliable Internet peers.
			