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

def mime_producer_lines (headers):
	lines = ['%s: %s\r\n' % (n, v) for n,v in headers.items ()]
	lines.append ('\r\n')
	return lines


class MIME_producer:
	
	mime_producer_lines = \
		mime_producer_headers = mime_producer_body = None
	
	def more (self):
		if self.mime_producer_lines:
			data = ''.join (self.mime_producer_lines)
			self.mime_producer_lines = None
			return data

		if self.mime_producer_body:
			return self.mime_producer_body.more ()
			
		return ''
		
	def producer_stalled (self):
		return (
			self.mime_producer_body == None or
			self.mime_producer_body.producer_stalled ()
			)

"""
def mime_producer_more (reactor):
	while True:
		data = reactor.mime_producer_body.more ()
		if data:
			yield data
			
		break
		
class MIME_producer_2 (Composite_producer):
	
	def __init__ (self, lines=None, headers=None, body=None):
		self.mime_producer_lines = lines or []
		self.mime_producer_headers = headers or {}
		self.mime_producer_body = body
		
	def mime_produce (self):
		self.composite_current = ''.join (
			lines.extend (mime_producer_lines (headers))
			)
		self.composite_body = mime_producer_more (self)
"""

# Simple transfert-encoding and content-encoding Producers

class Chunked_producer:

	"a producer for the 'chunked' transfer coding of HTTP/1.1."

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
			self.footers = '\r\n'.join (
				['0'] + footers
				) + '\r\n\r\n'
		else:
			self.footers = '0\r\n\r\n'
		self.producer_stalled = self.producer.producer_stalled

	def more (self):
		if self.producer:
			data = self.producer.more ()
			if data:
				return '%x\r\n%s\r\n' % (len (data), data)

			self.producer = None
			return self.footers
			
		return ''


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
		buffer = self.buffer + self.producer.more ()
		if buffer:
			buffer = string.replace (
				buffer, self.esc_from, self.esc_to
				)
			i = self.find_prefix_at_end (buffer, self.esc_from)
			if i:
				# we found a prefix
				self.buffer = buffer[-i:]
				return buffer[:-i]
			
			# no prefix, return it all
			self.buffer = ''
			return buffer
			
		return buffer


		