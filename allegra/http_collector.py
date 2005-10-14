# Copyright (C) 2005 Laurent A.V. Szyster
# 
# This library is free software; you can redistribute it and/or modify
# it under the terms of version 2.1 of the GNU Lesser General Public
# License as published by the Free Software Foundation.
# 
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307
# USA

""

from allegra.reactor import Buffer_reactor
from allegra.collector import Simple_collector, Length_collector
from allegra.mime_collector import mime_headers_map


class Chunk_collector:

	"a wrapping collector for chunked transfer encoding"

	collector_is_simple = 0
	chunk_extensions = None

	def __init__ (self, collector, set_terminator, headers=None):
		"insert a chunked collector between two MIME collectors"
		self.chunk_collector = collector
		self.set_terminator = set_terminator
		self.mime_collector_headers = headers or {}
		self.collect_incoming_data = self.chunk_collect_size
		self.chunk_size = ''
		self.chunk_trailers = None
		self.chunk_trailer = ''
		self.set_terminator ('\r\n')

	def chunk_collect_size (self, data):
		self.chunk_size += data

	def chunk_collect_trailers (self, data):
		self.chunk_trailer += data

	def found_terminator (self):
		if self.chunk_size == None:
			# end of a chunk, get next chunk-size
			self.set_terminator ('\r\n')
			self.chunk_size = ''
			self.collect_incoming_data = self.chunk_collect_size
			return False # continue ...
		
		if self.chunk_size == '0':
			# last chunk
			if self.chunk_trailers == None:
				self.chunk_trailers = []
				self.collect_incoming_data = self.chunk_collect_trailers
				return False # continue ...
			
			elif self.chunk_trailer:
				self.chunk_trailers.append (self.chunk_trailer)
				self.chunk_trailer = ''
				return False # continue ...
			
			elif self.chunk_trailers:
				self.mime_collector_headers.update (
					mime_headers_map (self.chunk_trailers)
					)
			self.chunk_collector.found_terminator ()
			self.set_terminator ('\r\n\r\n')
			del self.set_terminator
			return True # final!

		# end of chunk size, collect the chunk with the wrapped collector
		if self.chunk_size.find (';') > 0:
			(
				self.chunk_size, self.chunk_extensions
				) = self.chunk_size.split (';', 1)
		self.set_terminator (
			int (self.chunk_size, 16) + 2
			)
		self.chunk_size = None
		self.collect_incoming_data = self.chunk_collector.collect_incoming_data
		return False # continue ...


class HTTP_collector:

	"adds HTTP/1.0 and HTTP/1.1 collector wrapper for server and client channels"

	def http_collector_continue (self, collector):
		# decide wether and wich collector wrappers are needed
                if self.mime_collector_headers.get (
			'transfer-encoding', ''
			).lower () == 'chunked':
			# HTTP/1.1 only
			if not collector.collector_is_simple:
				collector = Simple_collector (collector)
			self.mime_collector_body = Chunk_collector (
				collector,
				self.set_terminator,
				self.mime_collector_headers
				)
		else:
			# HTTP/1.0 mostly
			content_length = self.mime_collector_headers.get (
				'content-length'
				)
			if content_length:
				if collector.collector_is_simple:
					self.mime_collector_body = collector
					self.set_terminator (int (content_length))
				else:
					self.mime_collector_body = Length_collector (
						collector, int (content_length)
						)
			else:
				# HTTP/1.0 connection closed
				self.mime_collector_body = collector
				self.set_terminator (None)
		return True # final!

"""
allegra/http_collector.py

the HTTP_collector implements mime_collector_continue and defines two
new interfaces:

	http_collector_continue
	http_collector_error

http_collector_continue is a boolean method that returns 0 if the HTTP
request or response has been collected, 1 if there is a body to
collect. this method is the place to implement the client or server
protocol logic.

http_collector_error is called when an error occurs in the collector(s)
managed by the HTTP_collector interface.

"""

