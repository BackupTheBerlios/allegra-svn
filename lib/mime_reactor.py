# Copyright (C) 2005-2007 Laurent A.V. Szyster
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

""

from allegra import (
	finalization, async_chat, collector, producer, reactor, async_client, 
        mime_headers
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

if __debug__:
        mime_collect_default = (lambda headers: collector.DEVNULL)
else:
        mime_collect_default = (lambda headers: collector.LOGINFO)

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
                self.mime_collector_body = mime_collect_default (
                        self.mime_collector_headers
                        )
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

        def __init__ (
                self, producer, escape_from='\r\n.\r\n', escape_to='\r\n..\r\n'
                ):
                self.escape = (lambda s: s.replace (escape_from, escape_to))
                self.escape_from = escape_from
                self.escape_buffer = ''
                self.producer = producer
                self.producer_stalled = self.producer.producer_stalled

        def more (self):
                buffer = self.escape_buffer + self.producer.more ()
                if buffer:
                        i = async_chat.find_prefix_at_end (
                                buffer, self.escape_from
                                )
                        if i > 0:
                                # we found a prefix
                                self.escape_buffer = buffer[-i:]
                                return self.escape (buffer[:-i])
                        
                        # no prefix, return it all
                        self.escape_buffer = ''
                        return self.escape (buffer)
                        
                return buffer
        
        
class Escaping_collector (object):

        "A collector that escapes a stream of characters"
        
        collector_is_simple = True

        def __init__ (
                self, collect, escape_from='\r\n..\r\n', escape_to='\r\n.\r\n'
                ):
                self.escape = (lambda s: s.replace (escape_from, escape_to))
                self.escape_from = escape_from
                self.escape_buffer = ''
                self.collector = collect

        def collect_incoming_data (self, data):
                buffer = self.escape_buffer + data
                i = async_chat.find_prefix_at_end (buffer, self.escape_from)
                if i > 0:
                        self.collector.collect_incoming_data (
                                self.escape (buffer[:-i])
                                )
                        self.escape_buffer = buffer[-i:]
                else:
                        self.collector.collect_incoming_data (
                                self.escape (buffer)
                                )
                        self.escape_buffer = ''

        def found_terminator (self):
                return self.collector.found_terminator ()


def multipart_generator (parts, boundary):
        for part in parts:
                yield boundary
        
                yield part
                
        yield boundary + '--'
        

def multipart_producer (parts, headers=None, glob=1<<14):
        boundary = '%x' % id (self)
        if headers == None:
                head = (
                        'MIME-Version: 1.0\r\n'
                        'Content-Type: multipart/mixed;'
                        ' boundary="%s"\r\n\r\n' % boundary
                        )
        else:
                headers['content-type'] = (
                        'multipart/mixed; boundary="%s"' % boundary
                        )
                head = ''.join (mime_headers.lines (headers))
        return producer.Composite (
                head, multipart_generator (
                        parts, '\r\n--%s' % boundary
                        ), glob
                )
                                

class MULTIPART_collector (object):
	
	collector_is_simple = False
        
        multipart_collect = None

        def __init__ (self, Collect):
                self.multipart_Collect = Collect
                self.multipart_buffer = ''
		self.multipart_boundary = '--' + \
			mime_headers.get_parameter (
				mime_collector.mime_collector_headers[
					'content-type'
					], 'boundary'
				)
                
        def collect_incoming_data (self, data):
                self.multipart_buffer += data
		
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
                        del self.collect_incoming_data
			return False

	def multipart_found_headers (self):
		headers = mime_headers.map (
			mime_headers.split (self.multipart_buffer)
			)
                collect = self.multipart_Collect (headers)
		if not collect.collector_is_simple:
			collect = collector.bind_complex (
                                collector.Simple (), collect
                                )
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
        

def multipart_collect_by_content_disposition (Collector=collector.File):
        def Collect (collector, headers):
                return Collector (mime_headers.get_parameter (
                        headers.setdefault (
                                'content-disposition',
                                'not available; name="%d"' % len (
                                        self.multipart_parts
                                        )
                                ), 'name'
                        ))
        return Collect


multipart_collectors = {}

def multipart_collect_by_content_types (collectors=multipart_collectors):
        def Collect (collector, headers):
                content_type, parameters = mime_headers.value_and_parameters (
                        headers.get ('content-type', 'text/plain')
                        )
                return collectors.get (
                        content_type, mime_collect_default
                        ) (headers)
        
        return Collect


# Peer Abstractions

class Pipeline (
        MIME_collector, async_chat.Dispatcher, async_client.Pipeline
        ):

        def __init__ (self):
                async_chat.Dispatcher.__init__ (self)
                self.pipeline_set ()
                self.set_terminator ('\r\n')
                self.mime_collector_buffer = ''
                
        __call__ = async_client.Pipeline.pipeline
                                        
        def handle_connect (self):
                "fill the pipeline's output_fifo if there are new requests"
                if self.pipeline_requests:
                        self.pipeline_wake_up ()
                        
        def handle_close (self):
                assert None == self.log ('{'
                        ' "requests": %d, "responses": %d,'
                        ' "pending": %d, "failed": %d'
                        ' }' % (
                                self.pipelined_requests, 
                                self.pipelined_responses,
                                len (self.pipeline_requests),
                                len (self.pipeline_responses)
                                ), 'debug'
                        )
                self.pipeline_close ()
                self.close ()

        def close (self):
                self.pipeline_close ()
                async_chat.Dispatcher.close (self)
                
        def mime_collector_continue (self):
                self.pipelined_responses += 1
                if self.pipeline_responses:
                        assert None == self.log (''.join ((
                                self.pipeline_responses[0][0],
                                '\r\n'.join (self.mime_collector_lines)
                                )), 'debug')
                        if not self.pipeline_responses.popleft (
                                )[1] (self.mime_collector_lines):
                                self.mime_collector_finalize ()
                else:
                        assert None == self.log (
                                self.mime_collector_lines[0], 'unexpected'
                                )
                return self.closing
                
        def mime_collector_finalize (self):
                self.mime_collector_lines = self.mime_collector_body = None
                if self.pipeline_requests:
                        self.pipeline_wake_up ()
                if self.pipeline_responses:
                        self.set_terminator (self.pipeline_responses[0][2])
                else:
                        self.set_terminator (None)
                return self.closing
        
        def pipeline_after_last (self, continuation):
                last = self.pipeline_requests.pop ()
                def after (response):
                        continuation ()
                        return last[1] (response)
                
                self.pipeline_requests.append ((last[0], after, last[2]))                               