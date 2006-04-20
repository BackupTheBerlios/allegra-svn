# Copyright 1996 by Sam Rushing
#
#                         All Rights Reserved
#
# Permission to use, copy, modify, and distribute this software and
# its documentation for any purpose and without fee is hereby
# granted, provided that the above copyright notice appear in all
# copies and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of Sam
# Rushing not be used in advertising or publicity pertaining to
# distribution of the software without specific, written prior
# permission.
#
# SAM RUSHING DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
# INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS, IN
# NO EVENT SHALL SAM RUSHING BE LIABLE FOR ANY SPECIAL, INDIRECT OR
# CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
# OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
# NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.


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


# Given 'haystack', see if any prefix of 'needle' is at its end.  This
# assumes an exact match has already been checked.  Return the number of
# characters matched.
# for example:
# f_p_a_e ("qwerty\r", "\r\n") => 1
# f_p_a_e ("qwertydkjf", "\r\n") => 0
# f_p_a_e ("qwerty\r\n", "\r\n") => <undefined>

def find_prefix_at_end (haystack, needle):
        l = len (needle) - 1
        while l and not haystack.endswith (needle[:l]):
                l -= 1
        return l
        #
        # this could maybe be made faster with a computed regex?
        # [answer: no; circa Python-2.0, Jan 2001]
        # new python:   28961/s
        # old python:   18307/s
        # re:        12820/s
        # regex:     14035/s


def collect (c):
        c.collector_stalled = False
        lb = len (c.ac_in_buffer)
        while lb:
                terminator = c.get_terminator ()
                if terminator is None or terminator == '':
                        c.collect_incoming_data (c.ac_in_buffer)
                        c.ac_in_buffer = ''
                elif isinstance (terminator, int):
                        n = terminator
                        if lb < n:
                                c.collect_incoming_data (c.ac_in_buffer)
                                c.ac_in_buffer = ''
                                c.terminator = c.terminator - lb
                        else:
                                c.collect_incoming_data (c.ac_in_buffer[:n])
                                c.ac_in_buffer = c.ac_in_buffer[n:]
                                c.terminator = 0
                                if c.found_terminator ():
                                        c.collector_stalled = True
                                        break

                else:
                        tl = len (terminator)
                        index = c.ac_in_buffer.find (terminator)
                        if index != -1:
                                if index > 0:
                                        c.collect_incoming_data (
                                                c.ac_in_buffer[:index]
                                                )
                                c.ac_in_buffer = c.ac_in_buffer[index+tl:]
                                if c.found_terminator ():
                                        c.collector_stalled = True
                                        break
                                
                        else:
                                index = find_prefix_at_end (
                                        c.ac_in_buffer, terminator
                                        )
                                if index:
                                        if index != lb:
                                                c.collect_incoming_data (
                                                        c.ac_in_buffer[:-index]
                                                        )
                                                c.ac_in_buffer = \
                                                        c.ac_in_buffer[-index:]
                                        break
                                        
                                else:
                                        c.collect_incoming_data (
                                                c.ac_in_buffer
                                                )
                                        c.ac_in_buffer = ''
                lb = len (c.ac_in_buffer)
        

def produce (c):
        while len (c.producer_fifo):
                p = c.producer_fifo[0]
                if p == None:
                        if c.ac_out_buffer == '':
                                c.producer_fifo.popleft ()
                                c.handle_close () # this *is* an event
                        return
                    
                elif type (p) == str:
                        c.producer_fifo.popleft ()
                        c.ac_out_buffer += p
                        return

                data = p.more ()
                if data:
                        c.ac_out_buffer += data
                        return
                    
                c.producer_fifo.popleft ()                        
                        
                        
class Async_chat (async_core.Async_dispatcher):

        ac_in_buffer_size = ac_out_buffer_size = 4096
        
        def __init__ (self, conn=None):
                self.ac_in_buffer = ''
                self.ac_out_buffer = ''
                self.producer_fifo = collections.deque ()
                async_core.Async_dispatcher.__init__ (self, conn)

        def __repr__ (self):
                return 'async-chat id="%x"' % id (self)
        
        collector_stalled = False
                
        #def readable (self):
        #        "predicate for inclusion in the poll loop for input"
        #        return (len (self.ac_in_buffer) <= self.ac_in_buffer_size)

        def readable (self):
                "predicate for inclusion in the poll loop for input"
                return not (
                        self.collector_stalled or
                        len (self.ac_in_buffer) > self.ac_in_buffer_size
                        )

        #def writable (self):
        #        "predicate for inclusion in the poll loop for output"
        #        return not (
        #                (self.ac_out_buffer == '') and
        #                not self.producer_fifo and 
        #                self.connected
        #                )

        def writable (self):
                "predicate for inclusion in the poll loop for output"
                try:
                        return not (
                                self.producer_fifo[
                                        0
                                        ].producer_stalled () and
                                self.connected
                                )
                
                except:
                        return not (
                                (self.ac_out_buffer == '') and 
                                not self.producer_fifo and 
                                self.connected
                                )

        def handle_read (self):
                "try to refill the input buffer and consume it"
                try:
                        data = self.recv (self.ac_in_buffer_size)
                except socket.error, why:
                        self.handle_error()
                        return

                self.ac_in_buffer += data
                self.async_collect ()

        def handle_write (self):
                "try to refill the output buffer and send it"
                obs = self.ac_out_buffer_size
                if (len (self.ac_out_buffer) < obs):
                        self.async_produce ()
                if self.ac_out_buffer and self.connected:
                        try:
                                sent = self.send (
                                        self.ac_out_buffer[:obs]
                                        )
                        except socket.error, why:
                                self.handle_error ()
                        else:
                                if sent:
                                        self.ac_out_buffer = \
                                                self.ac_out_buffer[sent:]
                        
        async_collect = collect

        async_produce = produce
        
        def push (self, p):
                "push a string or producer on the output queue, initiate send"
                assert type (p) == str or hasattr (p, 'more')
                self.producer_fifo.append (p)
                self.handle_write ()

        def close_when_done (self):
                """automatically close this channel once the outgoing queue 
                is empty, or handle close now if it is allready empty"""
                if len (self.producer_fifo) == 0:
                        self.handle_close () # when done is now!
                else:
                        self.producer_fifo.append (None)

        # The Async_chat Interface

        terminator = '\n'

        def set_terminator (self, terminator):
                self.terminator = terminator

        def get_terminator (self):
                return self.terminator

        def collect_incoming_data(self, data):
                assert None == self.log (data, 'collect-incoming-data')

        def found_terminator(self):
                assert None == self.log (
                        self.get_terminator (), 'found-terminator'
                        )
                return False # collector NOT stalled

# Note about this implementation
#
# This is a refactored version of asynchat.py as found in Python 2.4, and
# modified as to support stallable producers and collectors, loginfo and 
# finalization.
#
# Stallable Producer and Collector
#
# In order to support non-blocking asynchronous and synchronized peer, 
# the async_chat module introduces stallable collector and generalize
# the stallable producer of Medusa's proxy.
#
# Besides the fact that stallable reactors are a requirement for peers
# that do not block, they have other practical benefits. For instance,
# a channel with an collector_stalled and an empty output_fifo will not
# be polled for I/O.
#
# This implementation use collection.deque for output FIFO queues instead 
# of a class wrapper, and the push () method actually does what it is 
# supposed to do and pushes a string at the end that output queue, not a 
# Simple_producer instance.
#
# The channel's method collect_incoming_data is called to collect data 
# between terminators. Its found_terminator method is called whenever
# the current terminator is found, and if that method returns True, then
# no more buffer will be consumed until the channel's collector_stalled
# is not set to False by a call to async_collect.
