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
#

class Buffer_reactor (object):

	"a buffer reactor, usefull for asynchronous/synchronous proxy"

        collector_is_simple = 1
        buffer_reactor_complete = 0

        def __init__ (self, collector=None):
                self.buffer_reactor_buffers = []
                self.collect_incoming_data = \
                	self.buffer_reactor_buffers.append
                if collector != None:
                	self.buffer_reactor (collector)
                
        def buffer (self, data):
        	if data:
                	self.buffer_reactor_buffers.append (data)
         	else:
                	self.buffer_reactor_complete = True

	def found_terminator (self):
		self.buffer_reactor_complete = True

        def more (self):
                try:
                        return self.buffer_reactor_buffers.pop (0)
                    
                except IndexError:
                	self.buffer_react ()
                        return ''

        def producer_stalled (self):
                return (
			len (self.buffer_reactor_buffers) == 0 and
			self.buffer_reactor_complete == False
                        )

        def buffer_reactor (self, collector):
        	self.buffer_collector = collector
        	collector.collect_incoming_data = self.collect_incoming_data
  		collector.found_terminator = self.buffer_reactor_continue

	def buffer_reactor_continue (self):
		if self.buffer_collector.found_terminator ():
			self.buffer_reactor_complete = True
			self.buffer_collector = None
			
	def buffer_react (self):
		pass # to subclass
			
			
# Note about this implementation
#
# The Buffer_reactor is the only practical general-purpose implementation
# of the reactor interface:
#
#	__init__ ()
#	collect_incoming_data (data)
#	found_terminator ()
#	more ()
#	producer_stalled ()
#
# It adds two interfaces:
#
#	buffer_reactor (collector)
#	buffer_reactor_continue ()
#
# The first one is usefull to wrap any collector with a stallable buffered
# producer that can be pushed as a producer.
#
# Use of this implementation is simple. To push a collector as a producer
# onto another channel, simply do:
#
#	channel.push (Buffer_reactor (collector (...)))
#
# That's all folks.
#
# And it is also applicable for any kind of collector, not just channels. You
# may very well for instance wrap a buffer reactor around the MIME body
# collector of an HTTP client and set that reactor as the MIME body producer
# of an HTTP server reactor (see http_proxy.py).