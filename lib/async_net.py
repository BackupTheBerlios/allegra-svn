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

"http://laurentszyster.be/blog/async_net/"

import collections, socket

from allegra import async_core


class NetstringError (Exception): pass

def collect_net (next, buffer, collect, terminate):
        "consume a buffer of netstrings into a stallable collector sink"
        lb = len (buffer)
        if next > 0:
                if next > lb:
                        collect (buffer)
                        return next - lb, '', False # buffer more ...

                if buffer[next-1] == ',':
                        collect (buffer[:next-1])
                        if terminate (None):
                                return 0, buffer[next:], True # stop now!
                        
                else:
                        raise NetstringError, '3 missing comma'
                
                prev = next
        else:
                prev = 0
        while prev < lb:
                pos = buffer.find (':', prev)
                if pos < 0:
                        if prev > 0:
                                buffer = buffer[prev:]
                        if not buffer.isdigit ():
                                raise NetstringError, '1 not a netstring'
                        
                        return 0, buffer, False # buffer more ...
                        
                try:
                        next = pos + int (buffer[prev:pos]) + 2
                except:
                        raise NetstringError, '2 not a length'
                        
                pos += 1
                if next > lb:
                        if pos < lb:
                                collect (buffer[pos:])
                        return next - lb, '', False # buffer more
                
                elif buffer[next-1] == ',':
                        if terminate (buffer[pos:next-1]):
                                return 0, buffer[next:], True # stop now!
                        
                else:
                        raise NetstringError, '3 missing comma'
                      
                prev = next # continue ...
        return 0, '', False # buffer consumed.


class Dispatcher (async_core.Dispatcher_with_fifo):

        ac_in_buffer_size = 1 << 14 # sweet 16 kilobytes

        terminator = 0
        collector_stalled = False
                
        def __init__ (self):
                self.ac_in_buffer = ''
                self.ac_out_buffer = ''
                self.output_fifo = collections.deque ()

        def __repr__ (self):
                return 'async-net id="%x"' % id (self)
                
        def readable (self):
                "predicate for inclusion in the poll loop for input"
                return not (
                        self.collector_stalled or
                        len (self.ac_in_buffer) > self.ac_in_buffer_size
                        )

        def handle_read (self):
                "try to buffer more input and parse netstrings"
                try:
                        (
                                self.terminator, 
                                self.ac_in_buffer,
                                self.collector_stalled
                                ) = collect_net (
                                        self.terminator, 
                                        self.ac_in_buffer + self.recv (
                                                self.ac_in_buffer_size
                                                ),
                                        self.async_net_collect, 
                                        self.async_net_terminate
                                        )
                except NetstringError, error:
                        self.async_net_error (error)

        # The Async_net Interface

        def async_net_out (self, strings):
                "buffer as netstrings an iterable of 8-bit byte strings"
                self.ac_out_buffer += ''.join ((
                        '%d:%s,' % (len (s), s) for s in strings
                        ))

        def async_net_push (self, strings):
                "push an iterable of 8-bit byte strings for output"
                assert hasattr (strings, '__iter__')
                self.output_fifo.append (''.join ((
                        '%d:%s,' % (len (s), s) for s in strings
                        )))

        def async_net_pull (self):
                "try to consume the input netstrings buffered"
                if not self.ac_in_buffer:
                        self.collector_stalled = False
                        return
                
                try:
                        (
                                self.terminator, 
                                self.ac_in_buffer,
                                self.collector_stalled
                                ) = collect_net (
                                        self.terminator, 
                                        self.ac_in_buffer,
                                        self.async_net_collect, 
                                        self.async_net_terminate
                                        )
                except NetstringError, error:
                        self.async_net_error (error)

        async_net_in = ''

        def async_net_collect (self, bytes):
                "collect an incomplete netstring chunk into a buffer"
                self.async_net_in += bytes
                
        def async_net_terminate (self, bytes):
                "terminate a collected or buffered netstring and continue"
                if bytes == None:
                        bytes = self.async_net_in
                        self.async_net_in = ''
                return self.async_net_continue (bytes)

        def async_net_continue (self, bytes):
                "assert debug log of collected netstrings"
                assert None == self.log (bytes, 'async-net-continue')
                return False
        
        def async_net_error (self, message):
                "log netstrings error and close the channel when done"
                self.log (message, 'async-net-error')
                self.close_when_done ()
                self.collector_stalled = True
                assert None == self.log (self.ac_in_buffer, 'debug')
                
                