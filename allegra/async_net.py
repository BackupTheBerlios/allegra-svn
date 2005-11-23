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

import types, collections, socket

from allegra import async_core
                        
                        
class Async_net (async_core.Async_dispatcher):

        an_in_buffer_size = an_out_buffer_size = 4096
        
        async_net_buffer = 1<<16 # buffer maximum 64KB netstrings
        
        def __init__ (self, conn=None):
                self.an_in_buffer = ''
                self.an_out_buffer = ''
                self.an_fifo = collections.deque ()
                async_core.Async_dispatcher.__init__ (self, conn)

        def __repr__ (self):
                return 'async-net id="%x"' % id (self)
                
        def readable (self):
                "readable when the input buffer is not full"
                return (len (self.an_in_buffer) <= self.an_in_buffer_size)

        def writable (self):
                """writable when connected and the output buffer or queue 
                are not empty"""
                return not (
                        (self.an_out_buffer == '') and
                        not self.an_fifo and self.connected
                        )

        def handle_read (self):
                "buffer more input and try to parse netstrings"
                try:
                        data = self.recv (self.an_in_buffer_size)
                except socket.error, why:
                        self.handle_error()
                        return

                self.an_in_buffer += data
                while self.an_in_buffer:
                        pos = self.an_in_buffer.find (':')
                        if pos < 0:
                                if not self.an_in_buffer.isdigit ():
                                        self.async_net_error (
                                                'not a netstring'
                                                )
                                break
                                
                        try:
                                next = pos + int (self.an_in_buffer[:pos]) + 1
                        except:
                                self.async_net_error ('not a valid length')
                                return
                                
                        if next > self.async_net_buffer:
                                self.async_net_error ('buffer limit')
                                break
                                
                        if next >= len (self.an_in_buffer):
                                break
                        
                        if self.an_in_buffer[next] == ',':
                                self.async_net_continue (
                                        self.an_in_buffer[pos+1:next]
                                        )
                        else:
                                self.async_net_error ('missing end')        
                                break
                                
                        self.an_in_buffer = self.an_in_buffer[next+1:]

        def handle_write (self):
                "refill the output buffer and send it or close if done"
                obs = self.an_out_buffer_size
                while len (self.an_out_buffer) < obs and self.an_fifo:
                        strings = self.an_fifo.popleft ()
                        if strings == None:
                                if self.an_out_buffer == '':
                                        self.handle_close ()
                                        return
                                
                                self.an_fifo.append (None)        
                                break
                            
                        self.an_out_buffer += ''.join ([
                                '%d:%s,' % (len (s), s) for s in strings
                                ])
                if self.an_out_buffer and self.connected:
                        try:
                                sent = self.send (
                                        self.an_out_buffer[:obs]
                                        )
                        except socket.error, why:
                                self.handle_error ()
                        else:
                                if sent:
                                        self.an_out_buffer = \
                                                self.an_out_buffer[sent:]

        # A compatible interface with Async_chat.close_when_done used by
        # Allegra's TCP clients and servers implementation.
                        
        def close_when_done (self):
                """close this channel when previously queued strings have
                been sent, or close now if the queue is empty.
                """
                if len (self.an_fifo) == 0:
                        self.handle_close ()
                else:
                        self.an_fifo.append (None)

        # The Async_net Interface

        def async_net_push (self, strings):
                "push an iterable of 8-bit byte strings, initiate send"
                self.an_fifo.append (strings)
                self.handle_write ()

        def async_net_continue (self, data):
                "handle a netstring received"
                assert None == self.log (data, 'async-net-continue')

        def async_net_error (self, message):
                "handle netstring protocol errors"
                assert None == self.log (message, 'async-net-error')
                self.handle_close ()
                