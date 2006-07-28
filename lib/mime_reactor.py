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

from allegra import (
	finalization, collector, producer, reactor, mime_headers
        )


class MIME_producer (object):
	
	mime_producer_lines = \
		mime_producer_headers = mime_producer_body = None
	
	def more (self):
		data = ''.join (self.mime_producer_lines)
                if self.mime_producer_body == None:
                        self.mime_producer_lines == ()
                        return data
                
                self.more = self.mime_producer_body.more
                self.producer_stalled = \
                        self.mime_producer_body.producer_stalled
		return data
		
	def producer_stalled (self):
                return self.mime_producer_lines == None


class MIME_collector (object):
        
        """A collector implementation for all MIME collectors protocols,
        like MULTIPART but also POP, HTTP, etc ..."""
        
        collector_is_simple = False
        
        mime_collector_buffer = ''
        mime_collector_lines = \
                mime_collector_headers = mime_collector_body = None
                
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
                        self.mime_collector_lines = mime_headers.split (
                                self.mime_collector_buffer
                                )
                        self.mime_collector_buffer = ''
                        return self.mime_collector_continue ()
                        
                elif self.mime_collector_body.found_terminator ():
                        # if the MIME body final terminator is reached,
                        # finalize it and reset the state of the collector
                        # self.mime_collector_buffer = '' # ?
                        return self.mime_collector_finalize ()

        def mime_collector_continue (self):
                self.set_terminator (None)
                self.mime_collector_body = reactor.Buffer ()
                return False

        def mime_collector_finalize (self, reactor):
                # reset MIME collector's state
                self.mime_collector_headers = \
                        self.mime_collector_lines = \
                        self.mime_collector_body = None
                return True # stalled!


class MIME_reactor (
        MIME_collector, MIME_producer, finalization.Finalization
        ):

        def __init__ (self, headers=None, set_terminator=None):
                # first maybe attribute another set_terminator method,
                if set_terminator != None:
                        self.set_terminator = set_terminator
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
                        self.mime_collector_continue (headers)

        def mime_collector_continue (self, headers):
                self.mime_producer_headers = headers
                self.mime_collector_body = self.mime_producer_body = \
                        buffer.Reactor ()
                return False


class Escaping_producer (object):

        "A producer that escapes a stream of characters"

        # Common usage: escaping the CRLF.CRLF sequence in SMTP, NNTP, etc ...

        def __init__ (self, producer, esc_from='\r\n..', esc_to='\r\n.'):
                self.producer = producer
                self.esc_from = esc_from
                self.esc_to = esc_to
                self.buffer = ''
                self.producer_stalled = self.producer.producer_stalled

        def more (self):
                buffer = self.buffer + self.producer.more ()
                if buffer:
                        buffer = string.replace (
                                buffer, self.esc_from, self.esc_to
                                )
                        i = async_chat.find_prefix_at_end (
                                buffer, self.esc_from
                                )
                        if i:
                                # we found a prefix
                                self.buffer = buffer[-i:]
                                return buffer[:-i]
                        
                        # no prefix, return it all
                        self.buffer = ''
                        return buffer
                        
                return buffer


class Escaping_collector (object):

        "A collector that escapes a stream of characters"

        def __init__ (self, collect, esc_from='\r\n.', esc_to='\r\n..'):
                self.escaped = collect
                self.esc_from = esc_from
                self.esc_to = esc_to
                self.buffer = ''

        def collect_incoming_data (self, data):
                buffer = string.replace (
                        self.buffer + data, self.esc_from, self.esc_to
                        )
                i = async_chat.find_prefix_at_end (
                        buffer, self.esc_from
                        )
                if i > 0:
                        self.escaped.collect_incoming_data (buffer[-i:])
                        self.buffer = buffer[:-i]
                else:
                        self.escaped.collect_incoming_data (buffer)
                        self.buffer = ''

        def found_terminator (self):
                self.escaped.found_terminator


class MULTIPART_producer (producer.Composite):

        def __init__ (self, parts, headers=None):
                self.mime_producer_headers = headers or {}
                boundary = '\r\n\r\n--%x' % id (self)
                

class MULTIPART_collector (object):
	
	collector_is_simple = False
        multipart_collect = None

        def __init__ (self, mime_collector, Collect):
                self.multipart_Collect = Collect
                self.multipart_buffer = ''
                self.collect_incoming_data = \
                        self.multipart_buffer.__add__
		self.multipart_boundary = '\r\n\r\n--' + \
			mime_headers.get_parameter (
				mime_collector.mime_collector_headers[
					'content-type'
					], 'boundary'
				)
		self.set_terminator = mime_collector.set_terminator
		self.set_terminator (self.multipart_boundary[4:])
		
	def multipart_found_next (self):
		if self.multipart_buffer in ('--', ''):
			self.set_terminator = self.mime_collector = \
                                self.collect_incoming_data = \
                                self.found_terminator = None
			return True # end of the mulipart
		
		else:
			self.set_terminator ('\r\n\r\n')
			self.found_terminator = self.multipart_found_headers
                        self.multipart_buffer = ''
                        self.collect_incoming_data = \
                                self.multipart_buffer.__add__
			return False

	def multipart_found_headers (self):
		headers = mime_headers.map (
			mime_headers.split (self.multipart_buffer)
			)
                collect = self.multipart_Collect (headers)
		if not collect.collector_is_simple:
			collect = collector.Simple (collect)
		# self.multipart_parts.append (collect)
                self.multipart_collect = collect
		self.collect_incoming_data = collect.collect_incoming_data		
		self.found_terminator = self.multipart_found_boundary
		self.set_terminator (self.multipart_boundary)
		return False

	def multipart_found_boundary (self):
                self.multipart_collect.found_terminator ()
		self.set_terminator (2)
		self.found_terminator = self.multipart_found_next
		return False
                
        found_terminator = multipart_found_boundary 
        
        def multipart_collector (self):
                #name = mime_headers.get_parameter (
                #        headers.setdefault (
                #                'content-disposition',
                #                'not available; name="%d"' % len (
                #                        self.multipart_parts
                #                        )
                #                ), 'name'
                #        )
                content_type, parameters = mime_headers.value_and_parameters (
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


if __name__ == '__main__':
	from allegra import loginfo
	loginfo.log (
		'Allegra MIME Validator'
		' - Copyright 2005 Laurent A.V. Szyster'
                ' | Copyleft GPL 2.0', 
                'info'
                )
                
	def mime_collector_finalize (collector):
		while True:
			data = collector.mime_collector_body.more ()
			if data:
				sys.stdout.write (data)
			else:
				break
				
	mime_reactor = MIME_reactor ()
	mime_reactor.mime_collector_finalize = mime_collector_finalize
	simple_collector = Simple (mime_reactor)
	while True:
		data = sys.stdin.read (4096)
		if data:
			simple_collector.collect_incoming_data (data)
		else:
			break
	
	# Simply pipes a MIME or MIME/MULTIPART message from STDIN to STDOUT
	# collecting its parts and reproducing the input. Finalization(s) are
	# dumped to STDERR.
			
# A MIME reactor that uses a reactor.Buffer to proxy the collected
# headers and body to an asynchat channel simply by pushing the
# reactor in its output_fifo queue. It may be used to proxy any
# kind of MIME protocols, including HTTP, SMTP, POP3, etc.
#
# The lifecycle of a one way MIME proxy is usally this one:
#
#	0. instanciated, completed and set as its mime_collector_body
#          by the MIME collector channel, with a Buffer as body
#	1. pushed to the MIME producer channel with its mime_producer_body
#	   set to its mime_collector_body
#	2. dereferenced by the collector channel when collected
#	3. dereferenced by the producer channel when produced
#	4. finalized
#
# In the case of a two-way HTTP proxy, the finalization of a request
# reactor consists in instanciating a response reactor and pushing
# it back to the original collector channel.
#
# A MIME server can also be considered a one-way proxy using the same
# channel to collect requests from and produce responses to ;-)
#
#	0. instanciated, completed and and set as its mime_collector_body
#          by the MIME collector channel if there is a body to collect
#	1. pushed to the server channel
#	2. dereferenced by the server channel when produced
#	3. finalized
#
# The full implication of that original design of a MIME server, is
# that you can pipeline HTTP/1.1 requests like POST and PUT and still
# produce the response headers before the request's body as been
# collected.
#
# Of course a MIME client can be viewed in the same perspective:
#
#	0. instanciated and completed by a MIME client channel
#	1. pushed to the client channel
#	2. dereferenced by the client channel when collected
#	3. finalized
#

