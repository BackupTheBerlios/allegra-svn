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

from types import StringType, GeneratorType
from exceptions import StopIteration	


class Simple_producer:
	
	"producer for a string"

	def __init__ (self, data, buffer_size=1<<16):
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


class File_producer:
	
	"producer wrapper for file[-like] objects"

	def __init__ (self, file, buffer_size=1<<16):
		self.file = file
		self.buffer_size = buffer_size

	def more (self):
		return self.file.read (self.buffer_size)

	def producer_stalled (self):
		return False
	

class Composite_producer:
	
	# This is a more "modern" composite producer than the original
	# one, with support for stalled producers and generators. it is the
	# bread & butter of Allegra's PRESTo! with the Buffer_reactor.
	#
	# The composite producer let its accessor mix strings and producers
	# at will, to compose the message body, preceded by a single string
	# for the head. Taking a generator for the body parts, instanciation
	# of the composing strings and producers may take place at the last
	# moment, when bandwith is available for the consumer.
	# 
	# Finally, note that the producer "globs" strings until a producer
	# is found, producing an "optimal" stream by reducing the number
	# of calls to send without possibly blocking on stalled producers.
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
	
        def __init__ (self, head, body, glob=16384):
        	assert (
        		type (head) == StringType and 
        		type (body) == GeneratorType
        		)
        	self.composite_current = head
                self.composite_generator = body
                self.composite_glob = glob
                
 	def composite_more_string (self):
 		data = self.composite_current
 		while len (data) < self.composite_glob:
	        	try:
	        		self.composite_current = \
	        			self.composite_generator.next ()
	  		except StopIteration:
	  			self.composite_current = ''
	  			break

	        	if hasattr (self.composite_current, 'more'):
	        		self.more = self.composite_more_producer
	        		break
	        		
	  		data += self.composite_current
 		return data

	more = composite_more_string
 		
	def composite_more_producer (self):
		while 1:
			data = self.composite_current.more ()
			if data:
				return data
				
	        	try:
	        		self.composite_current = \
	        			self.composite_generator.next ()
	  		except StopIteration:
	  			self.composite_current = ''
	  			return ''
	  			
	        	if not hasattr (self.composite_current, 'more'):	
	        		self.more = self.composite_more_string
	 			return self.more ()
	               
	def producer_stalled (self):
		return (
			self.more == self.composite_more_producer and
			self.composite_current.producer_stalled ()
			)

	# Note that this class also makes the original lines, buffer and
	# globbing producer redundant.


# Simple transfert-encoding and content-encoding Producers

class Chunked_producer:

	"a producer that implements the 'chunked' transfer coding for HTTP/1.1."

	# Original comment of Sam Rushing
	#
	# "HTTP 1.1 emphasizes that an advertised Content-Length header MUST
	#  be correct.  In the face of Strange Files, it is conceivable that
	#  reading a 'file' may produce an amount of data not matching that
	#  reported by os.stat() [text/binary mode issues, perhaps the file is
	#  being appended to, etc..]  This makes the chunked encoding a True
	#  Blessing, and it really ought to be used even with normal files.
	#  How beautifully it blends with the concept of the producer."
	#
	# And how beautifully he implemented it!
	
	def __init__ (self, producer, footers=None):
		self.producer = producer
		if footers:
			self.footers = '\r\n'.join (['0'] + footers) + '\r\n\r\n'
		else:
			self.footers = '0\r\n\r\n'
		self.producer_stalled = self.producer.producer_stalled

	def more (self):
		if self.producer:
			data = self.producer.more ()
			if data:
				return '%x\r\n%s\r\n' % (len (data), data)
			
			else:
				self.producer = None
				return self.footers
			
		else:
			return ''

	def content_length (self):
		return len (self.footers) + self.producer.content_length ()


# Not used yet ...

class Escaping_producer:

	"A producer that escapes a sequence of characters"

	# Common usage: escaping the CRLF.CRLF sequence in SMTP, NNTP, etc ...

	def __init__ (self, producer, esc_from='\r\n.', esc_to='\r\n..'):
		self.producer = producer
		self.esc_from = esc_from
		self.esc_to = esc_to
		self.buffer = ''
		from asynchat import find_prefix_at_end
		self.find_prefix_at_end = find_prefix_at_end
		self.producer_stalled = self.producer.producer_stalled

	def more (self):
		esc_from = self.esc_from
		esc_to   = self.esc_to
		buffer = self.buffer + self.producer.more ()
		if buffer:
			buffer = string.replace (buffer, esc_from, esc_to)
			i = self.find_prefix_at_end (buffer, esc_from)
			if i:
				# we found a prefix
				self.buffer = buffer[-i:]
				return buffer[:-i]
			
			else:
				# no prefix, return it all
				self.buffer = ''
				return buffer
			
		else:
			return buffer

	def content_length (self):
		return self.producer.content_length ()


class Encoding_producer:

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

			