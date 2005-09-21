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
from allegra.collector import Simple_collector


# First a few MIME header parsers, obvious candidate for C implementation

def mime_headers_split (string):
	# cleanse and split a string of MIME headers into lines
	#
	return string.replace ('\t', ' ').split ('\r\n')

def mime_headers_map (lines):
	# map a sequence of cleansed MIME header lines into a dictionnary
	#
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
        # extract the tuple ('value', {'name'|0..n-1:'parameter'})
        # from a MIME header line.
        #
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
	# get the value of a parameter 'name' in a given header line
	#
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
	
	# A collector implementation for all MIME collectors protocols,
	# like SMTP, HTTP, etc ...
	
	collector_is_simple = 0
	
	mime_collector_buffer = ''
	mime_collector_lines = None
	mime_collector_body = None

	def __init__ (self, headers=None, set_terminator=None):
		if set_terminator != None:
			self.set_terminator = set_terminator
		if headers == None:
			self.set_terminator ('\r\n\r\n')
		else:
			self.mime_collector_headers = headers
			self.mime_collector_body = self.mile_collector_continue ()

	def collect_incoming_data (self, data):
		# collect the MIME body or its headers
		if self.mime_collector_body:
			self.mime_collector_body.collect_incoming_data (data)
		else:
			self.mime_collector_buffer += data

	def found_terminator (self):
		if self.mime_collector_body:
			# if the MIME body final terminator is reached,
			# finalize it and reset the state of the collector
			if self.mime_collector_body.found_terminator ():
				self.mime_collector_finalize ()
				self.mime_collector_buffer = ''
				self.set_terminator ('\r\n\r\n')
		else:
			# MIME headers collected, clear the buffer, split the
			# headers and continue ...
			self.mime_collector_lines = mime_headers_split (
				self.mime_collector_buffer
				)
			self.mime_collector_buffer = ''
			self.mime_collector_body = self.mime_collector_continue ()

	def mime_collector_continue (self):
		return Buffer_reactor ()

	def mime_collector_finalize (self, collector):
		self.mime_collector_headers = \
			self.mime_collector_body = \
			self.mime_collector_lines = None
	

class MULTIPART_collector:
	
	# This is a complex MIME/MULTIPART collector that collects the parts
	# encoded in

	collector_is_simple = 0

        def __init__ (self, mime_collector):
                self.multipart_buffer = ''
                self.multipart_part = None
                self.multipart_parts = {}
		self.multipart_boundary = '\r\n\r\n--' + mime_headers_get_parameter (
			mime_collector.mime_collector_headers['content-type'], 'boundary'
			)
		self.set_terminator = mime_collector.set_terminator
		self.set_terminator (self.multipart_boundary[4:])
		
	def multipart_MIME_collector (self, headers):
		#name = mime_headers_get_parameter (
		#	headers.setdefault (
		#		'content-disposition',
		#		'not available; name="%d"' % len (self.multipart_parts)
		#		), 'name'
		#	)
		content_type, parameters = mime_headers_value_and_parameters (
			headers.get ('content-type', 'text/plain')
			)
		if content_type == 'mime/multipart':
			return MULTIPART_collector
			
		return MIME_collector
		
        def multipart_collect_buffer (self, data):
		self.multipart_buffer += data

	def multipart_found_next (self):
		if self.multipart_buffer == '--':
			return 1 # end of the mulipart
		
		else:
			self.set_terminator ('\r\n\r\n')
			self.found_terminator = self.multipart_found_headers
			self.collect_incoming_data = self.multipart_collect_buffer
			return 0

	def multipart_found_headers (self):
		headers = mime_headers_map (
			mime_headers_split (self.multipart_buffer)
			)
		MIME_collector = self.multipart_MIME_collectors (headers)
		collector = MIME_collector (headers)
		if not MIME_collector.collector_is_simple:
			collector = Simple_collector (collector)
		self.multipart_parts.append (collector)
		self.collect_incoming_data = collector.collect_incoming_data		
		self.found_terminator = self.multipart_found_boundary
		self.set_terminator (self.boundary)
		return 0

	def multipart_found_boundary (self):
		self.set_terminator (2)
		self.found_terminator = self.multipart_found_next
		return 0
			

