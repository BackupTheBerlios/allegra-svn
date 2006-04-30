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

import collections, socket

from allegra import async_core


class NetstringError (Exception): pass

def netcollect (next, buffer, collect, terminate):
        "consume a buffer of netstrings into a collector sink"
        lb = len (buffer)
        if next > 0:
                if next > lb:
                        collect (buffer)
                        return next - lb, '' # buffer more ...

                if buffer[next] == ',':
                        collect (buffer[:next])
                        if terminate (None):
                                return 0, buffer[next+1:] # stop now!
                        
                else:
                        raise NetstringError, '3 missing end'
                
                prev = next + 1
        else:
                prev = 0
        while prev < lb:
                pos = buffer.find (':', prev)
                if pos < 0:
                        if prev > 0:
                                buffer = buffer[prev:]
                        if not buffer.isdigit ():
                                raise NetstringError, '1 not a netstring'
                        
                        return 0, buffer # buffer more ...
                        
                try:
                        next = pos + int (buffer[prev:pos]) + 1
                except:
                        raise NetstringError, '2 not a length'
                        
                if next >= lb:
                        collect (buffer[pos+1:])
                        return next - lb, '' # buffer more
                
                elif buffer[next] == ',':
                        if terminate (buffer[pos+1:next]):
                                return 0, buffer[next+1:] # stop now!
                        
                else:
                        raise NetstringError, '3 missing end'
                      
                prev = next + 1 # continue ...
        return 0, '' # buffer consumed.


class Async_net (async_core.Async_dispatcher):

        ac_in_buffer_size = 1<<14
        ac_out_buffer_size = 4096
        
        terminator = 0
        
        def __init__ (self, conn=None):
                self.ac_in_buffer = ''
                self.ac_out_buffer = ''
                self.netstrings_fifo = collections.deque ()
                async_core.Async_dispatcher.__init__ (self, conn)

        def __repr__ (self):
                return 'async-net id="%x"' % id (self)
                
        def readable (self):
                "readable when the input buffer is not full"
                return (len (self.ac_in_buffer) <= self.ac_in_buffer_size)

        def writable (self):
                """writable when connected and the output buffer or queue 
                are not empty"""
                return not (
                        (self.ac_out_buffer == '') and
                        not self.netstrings_fifo and self.connected
                        )

        def handle_read (self):
                "try to buffer more input and parse netstrings"
                try:
                        data = self.recv (self.ac_in_buffer_size)
                except socket.error, why:
                        self.handle_error()
                        return

                self.ac_in_buffer += data
                self.async_net_resume ()

        def handle_write (self):
                "refill the output buffer, try to send it or close if done"
                obs = self.ac_out_buffer_size
                buffer = self.ac_out_buffer
                fifo = self.netstrings_fifo
                while len (buffer) < obs and fifo:
                        strings = fifo.popleft ()
                        if strings == None:
                                if buffer == '':
                                        self.handle_close ()
                                        return
                                
                                else:
                                        fifo.append (None)
                                        break
        
                        buffer += ''.join ((
                                '%d:%s,' % (len (s), s) for s in strings
                                ))
                if buffer and self.connected:
                        try:
                                sent = self.send (buffer[:obs])
                        except socket.error, why:
                                self.handle_error ()
                        else:
                                if sent:
                                        self.ac_out_buffer = buffer[sent:]
                                else:
                                        self.ac_out_buffer = buffer
                else:
                        self.ac_out_buffer = buffer

        # A compatible interface with Async_chat.close_when_done used by
        # Allegra's TCP clients and servers implementation.
                        
        def close_when_done (self):
                """close this channel when previously queued strings have
                been sent, or close now if the queue is empty.
                """
                if len (self.netstrings_fifo) == 0:
                        self.handle_close ()
                else:
                        self.netstrings_fifo.append (None)

        # The Async_net Interface

        def async_net_out_buffer (self, strings):
                "buffer netstrings of an iterable of 8-bit byte strings"
                self.ac_out_buffer += ''.join ((
                        '%d:%s,' % (len (s), s) for s in strings
                        ))

        def async_net_push (self, strings):
                "push an iterable of 8-bit byte strings for output"
                assert hasattr (strings, '__iter__')
                self.netstrings_fifo.append (strings)

        def async_net_resume (self):
                "try to consume the input netstrings buffered"
                try:
                        self.terminator, self.ac_in_buffer = netcollect (
                                self.terminator, 
                                self.ac_in_buffer,
                                self.async_net_collect, 
                                self.async_net_terminate
                                )
                except NetstringError, error:
                        self.async_net_error (error)

        async_net_in_buffer = ''

        def async_net_collect (self, bytes):
                "collect an incomplete netstring chunk into a buffer"
                self.async_net_in_buffer += bytes
                
        def async_net_terminate (self, bytes):
                "terminate a collected or buffered netstring"
                if bytes == None:
                        self.async_net_continue (self.async_net_in_buffer)
                        self.async_net_in_buffer = ''
                else:
                        self.async_net_continue (bytes)

        def async_net_continue (self, bytes):
                "assert debug log of collected netstrings"
                assert None == self.log (bytes, 'async-net-continue')
        
        def async_net_error (self, message):
                "log netstrings error and close the channel"
                self.log (message, 'async-net-error')
                self.handle_close ()
             
                
# Optimized Netstrings Stream
#
# To produce a stream of netstrings for what is essentially a packet protocol
# like TCP, the optimum is to queue iterables of strings, "scan" it to build
# a buffer and rely on CPython's optimization of incrementation ...
#
# It may be even faster to just write directly to the buffer when iterables
# are not generators that the application would prefer to execute when the
# channel is writable (in order to ration processing and memory along I/O,
# providing reliable time sharing for slow network applications and 
# delivering the freshest possible response state to all peers).
#
# So, there is an async_net_buffer method for simpler netstring channels.
#
# Note that it may also be applied to bypass the netstrings fifo, giving
# practically two levels of priority: one for what is itered and buffered 
# immediately and one for what is queued to be itered when I/O is available.
#
# 