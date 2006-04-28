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

def collect (c, buffer):
        while buffer:
                pos = buffer.find (':')
                if pos < 0:
                        if not buffer.isdigit ():
                                c.async_net_error ('1 not a netstring')
                                return ''
                        
                        return buffer
                        
                try:
                        next = pos + int (buffer[:pos]) + 1
                except:
                        c.async_net_error ('2 not a length')
                        return ''
                        
                if next >= len (buffer):
                        if next > c.ac_in_buffer_size:
                                c.async_net_error ('3 buffer limit')
                                return ''
                                
                        return buffer # ... buffer more
                
                elif buffer[next] == ',':
                        if c.async_net_continue (buffer[pos+1:next]):
                                return buffer[next+1:]
                        
                else:
                        c.async_net_error ('4 missing end')
                        return ''
                        
                buffer = buffer[next+1:]
                #
                # TODO: optimize this method to avoid consuming
                #       the buffer this way, by scanning it instead
                #       but that's a little bit more tricky ...
        return buffer


class Async_net (async_core.Async_dispatcher):

        ac_in_buffer_size = 1<<14
        ac_out_buffer_size = 4096
        
        def __init__ (self, conn=None):
                self.ac_in_buffer = ''
                self.ac_out_buffer = ''
                self.netstrings_fifo = collections.deque ()
                # self.async_net_push = self.netstrings_fifo.append
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

                self.ac_in_buffer = collect (self, self.ac_in_buffer + data)

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

        def async_net_push (self, strings):
                "push an iterable of 8-bit byte strings, initiate send"
                self.netstrings_fifo.append (strings)
                # self.handle_write ()

        def async_net_continue (self, data):
                "handle a netstring received"
                assert None == self.log (data, 'async-net-continue')
                return False

        def async_net_error (self, message):
                "handle netstring protocol errors"
                assert None == self.log (message, 'async-net-error')
                self.handle_close ()