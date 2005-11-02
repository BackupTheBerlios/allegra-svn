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

from allegra.reactor import Buffer_reactor
from allegra.collector import Simple_collector, Length_collector


# First a few MIME header parsers, obvious candidate for C implementation

def mime_headers_split (string):
	"cleanse and split a string of MIME headers into lines"
	return string.replace ('\t', ' ').split ('\r\n')

def mime_headers_map (lines):
	"map a sequence of cleansed MIME header lines into a dictionnary"
	headers = {}
        n = None
        v = ''
        for line in lines:
                if 0 < line.find (':') < line.find (' '):
                        if headers.has_key (n):
                                try:
                                        headers[n].append (v)
                                except:
                                        headers[n] = [headers[n], v]
                        else:
                                headers[n] = v
                        n, v = line.split (':', 1)
                        n = n.strip ().lower ()
                        v = v.strip ()
		else:
			v += line
        if headers.has_key (n):
                try:
                        headers[n].append (v)
                except:
                        headers[n] = [headers[n], v]
        else:
                headers[n] = v
	del headers[None] # remove collected garbage lines if any
        return headers
        
        
def mime_headers_options (headers, name):
	options = headers.get (name)
	if options == None:
		return (None, )
		
	return options.split (',')
	

def mime_headers_preferences (headers, name):
	options = headers.get (name)
	if options == None:
		return (None, )
		
	preferences = []
	for option in options.split (','):
		q in option.split (';')
		if len (q) == 2 and q[1].startswith ('q='):
			preferences.append ((float (q[1][2:]), q[0]))
		else:
			preferences.append ((1.0, q[0]))
	preferences.sort ()
	return [q[1] for q in preferences]
	

def mime_headers_value_and_parameters (line):
        """extract the tuple ('value', {'name'|0..n-1:'parameter'}) from a 
        MIME header line."""
        parameters = {}
        parts = [p.strip () for p in line.split (';')]
        for parameter in parts[1:]:
                if parameter.find ('=') > 0:
                        n, v = parameter.split ('=')
                        if v[0] == '"':
                                parameters[n] = v[1:-1]
                        else:
                                parameters[n] = v
                else:
                        parameters[len (parameters)] = v
        return parts[0], parameters

def mime_headers_get_parameter (line, name):
	"get the value of a parameter 'name' in a given header line"
        parts = [p.strip () for p in line.split (';')]
        for parameter in parts[1:]:
                if parameter.find ('=') > 0:
                        n, v = parameter.split ('=')
                        if n.lower () == name.lower ():
				if v[0] == '"':
					return v[1:-1]
				
				else:
					return v
				
        return None


class MIME_collector:
	
	"""A collector implementation for all MIME collectors protocols,
	like MULTIPART but also SMTP, HTTP, etc ..."""
	
	collector_is_simple = False
	
	mime_collector_buffer = ''
	mime_collector_lines = None
	mime_collector_body = None

	def __init__ (
		self, headers=None, set_terminator=None, Collector=None
		):
		# first maybe attribute another set_terminator method,
		if set_terminator != None:
			self.set_terminator = set_terminator
		self.MIME_collector = Collector or Buffer_reactor
		if headers == None:
			# if no headers have been provided, get them and so
			# set the terminator to '\r\n\r\n'
			#
			self.set_terminator ('\r\n\r\n')
		else:
			# or consider the headers as allready collected and
			# immediately set the body collector to the result of
			# the continuation ...
			#
			self.mime_collector_headers = headers
			self.mime_collector_body = \
				self.mime_collector_continue ()
		#
		# This "akward" initialisation does actually match a very
		# practical application of MULTIPART collector. And it also 
		# serves decently when mixing with an asynchat channel to
		# form HTTP or SMTP servers and clients. 

	def collect_incoming_data (self, data):
		# collect the MIME body or its headers
		if self.mime_collector_body == None:
			self.mime_collector_buffer += data
		else:
			self.mime_collector_body.collect_incoming_data (data)

	def found_terminator (self):
		if self.mime_collector_body == None:
			# MIME headers collected, clear the buffer, split the
			# headers and continue ...
			self.mime_collector_lines = mime_headers_split (
				self.mime_collector_buffer
				)
			self.mime_collector_buffer = ''
			self.mime_collector_body = \
				self.mime_collector_continue ()
		else:
			# if the MIME body final terminator is reached,
			# finalize it and reset the state of the collector
			if self.mime_collector_body.found_terminator ():
				self.mime_collector_finalize ()
				self.mime_collector_buffer = ''
				self.set_terminator ('\r\n\r\n')

	def mime_collector_continue (self):
		return self.MIME_collector ()

	def mime_collector_finalize (self, collector):
		self.mime_collector_headers = \
			self.mime_collector_body = \
			self.mime_collector_lines = None
	

class MULTIPART_collector:
	
	"A recursive MIME/MULTIPART collector wrapper"

	collector_is_simple = False

        def __init__ (self, mime_collector):
        	self.mime_collector = mime_collector
                self.multipart_buffer = ''
                self.multipart_part = None
                self.multipart_parts = {}
		self.multipart_boundary = '\r\n\r\n--' + \
			mime_headers_get_parameter (
				mime_collector.mime_collector_headers[
					'content-type'
					], 'boundary'
				)
		self.set_terminator = mime_collector.set_terminator
		self.set_terminator (self.multipart_boundary[4:])
		
        def multipart_collect (self, data):
		self.multipart_buffer += data

	def multipart_found_next (self):
		if self.multipart_buffer == '--':
			self.set_terminator = self.mime_collector = None
			return True # end of the mulipart
		
		else:
			self.set_terminator ('\r\n\r\n')
			self.found_terminator = self.multipart_found_headers
			self.collect_incoming_data = self.multipart_collect
			return False

	def multipart_found_headers (self):
		headers = mime_headers_map (
			mime_headers_split (self.multipart_buffer)
			)
		#name = mime_headers_get_parameter (
		#	headers.setdefault (
		#		'content-disposition',
		#		'not available; name="%d"' % len (
		#			self.multipart_parts
		#			)
		#		), 'name'
		#	)
		content_type, parameters = mime_headers_value_and_parameters (
			headers.get ('content-type', 'text/plain')
			)
		if content_type == 'mime/multipart':
			collector = MULTIPART_collector (self)
		else:
			collector = MIME_collector (
				headers, 
				self.set_terminator,
				self.mime_collector.mime_collector_continue
				)
		if not collector.collector_is_simple:
			collector = Simple_collector (collector)
		self.multipart_parts.append (collector)
		self.collect_incoming_data = collector.collect_incoming_data		
		self.found_terminator = self.multipart_found_boundary
		self.set_terminator (self.multipart_boundary)
		return False

	def multipart_found_boundary (self):
		self.set_terminator (2)
		self.found_terminator = self.multipart_found_next
		return False


class Chunk_collector:

	"a wrapping collector for chunked transfer encoding"

	collector_is_simple = False
	
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
				self.collect_incoming_data = \
					self.chunk_collect_trailers
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

		# end of chunk size, collect the chunk with the wrapped 
		# collector
		#
		if self.chunk_size.find (';') > 0:
			(
				self.chunk_size, self.chunk_extensions
				) = self.chunk_size.split (';', 1)
		self.set_terminator (
			int (self.chunk_size, 16) + 2
			)
		self.chunk_size = None
		self.collect_incoming_data = \
			self.chunk_collector.collect_incoming_data
		return False # continue ...
