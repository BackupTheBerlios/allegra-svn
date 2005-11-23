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

import types, collections, socket

from allegra import async_core


def refill_buffer (channel):
        if len (channel.producer_fifo):
                p = channel.producer_fifo[0]
                if p is None:
                        if channel.ac_out_buffer == '':
                                channel.producer_fifo.popleft ()
                                channel.handle_close () # this *is* an event
                        return
                    
                elif type (p) is types.StringType:
                        channel.producer_fifo.popleft ()
                        channel.ac_out_buffer += p
                        return

                data = p.more ()
                if data:
                        channel.ac_out_buffer += data
                        return
                    
                else:
                        channel.producer_fifo.popleft ()
                        return True
                        
                        
# Given 'haystack', see if any prefix of 'needle' is at its end.  This
# assumes an exact match has already been checked.  Return the number of
# characters matched.
# for example:
# f_p_a_e ("qwerty\r", "\r\n") => 1
# f_p_a_e ("qwertydkjf", "\r\n") => 0
# f_p_a_e ("qwerty\r\n", "\r\n") => <undefined>

def find_prefix_at_end (haystack, needle):
        l = len(needle) - 1
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


def consume_buffer (channel):                        
        lb = len (channel.ac_in_buffer)
        terminator = channel.get_terminator ()
        if terminator is None or terminator == '':
                # no terminator, collect it all
                channel.collect_incoming_data (channel.ac_in_buffer)
                channel.ac_in_buffer = ''
        elif isinstance (terminator, int):
                # numeric terminator
                n = terminator
                if lb < n:
                        channel.collect_incoming_data (
                                channel.ac_in_buffer
                                )
                        channel.ac_in_buffer = ''
                        channel.terminator = self.terminator - lb
                else:
                        channel.collect_incoming_data (
                                channel.ac_in_buffer[:n]
                                )
                        channel.ac_in_buffer = channel.ac_in_buffer[n:]
                        channel.terminator = 0
                        channel.found_terminator ()
        else:
                # 3 cases:
                # 1) end of buffer matches terminator exactly:
                #    collect data, transition
                # 2) end of buffer matches some prefix:
                #    collect data to the prefix
                # 3) end of buffer does not match any prefix:
                #    collect data
                terminator_len = len (terminator)
                index = channel.ac_in_buffer.find (terminator)
                if index != -1:
                        # we found the terminator
                        if index > 0:
                                # don't bother reporting the empty string 
                                # (source of subtle bugs)
                                channel.collect_incoming_data (
                                        channel.ac_in_buffer[:index]
                                        )
                        channel.ac_in_buffer = \
                                channel.ac_in_buffer[index+terminator_len:]
                        # This does the Right Thing if the terminator is
                        # changed here.
                        channel.found_terminator ()
                else:
                        # check for a prefix of the terminator
                        index = find_prefix_at_end (
                                channel.ac_in_buffer, terminator
                                )
                        if index:
                                if index != lb:
                                        # we found a prefix, collect up to
                                        # the prefix
                                        channel.collect_incoming_data (
                                                channel.ac_in_buffer[:-index]
                                                )
                                        channel.ac_in_buffer = \
                                                channel.ac_in_buffer[-index:]
                                return False
                                
                        else:
                                # no prefix, collect it all
                                channel.collect_incoming_data (
                                        channel.ac_in_buffer
                                        )
                                channel.ac_in_buffer = ''
        return len (channel.ac_in_buffer) > 0
        
                        
class Async_chat (async_core.Async_dispatcher):

        ac_in_buffer_size = ac_out_buffer_size = 4096
        
        def __init__ (self, conn=None):
                self.ac_in_buffer = ''
                self.ac_out_buffer = ''
                self.producer_fifo = collections.deque ()
                async_core.Async_dispatcher.__init__ (self, conn)

        def __repr__ (self):
                return 'async-chat id="%x"' % id (self)
                
        def readable (self):
                "predicate for inclusion in the readable for select()"
                return (len (self.ac_in_buffer) <= self.ac_in_buffer_size)

        def writable (self):
                "predicate for inclusion in the writable for select()"
                return not (
                        (self.ac_out_buffer == '') and
                        not self.producer_fifo and self.connected
                        )
                #
                # return 
                # (
                #        len (self.ac_out_buffer) or 
                #        len (self.producer_fifo) or 
                #        (not self.connected)
                #        ), 
                #
                # this is about twice as fast, though not as clear.

        def writable_for_stalled (self):
                return not (
                        (self.ac_out_buffer == '') and
                        (
                                len (self.producer_fifo) == 0 or
                                self.producer_fifo[0].producer_stalled ()
                                ) and
                        self.connected
                        )

        def handle_read (self):
                try:
                        data = self.recv (self.ac_in_buffer_size)
                except socket.error, why:
                        self.handle_error()
                        return

                # Continue to search for self.terminator in self.ac_in_buffer,
                # while calling self.collect_incoming_data.  The while loop
                # is necessary because we might read several data+terminator
                # combos with a single recv(1024).
                #
                #assert None == self.log (
                #        'handle-read read="%d" buffered="%d"' % (
                #                len (data), len (self.ac_out_buffer)
                #                ),
                #        'debug'
                #        )
                self.ac_in_buffer += data
                while self.ac_consume_buffer ():
                        pass

        def handle_write (self):
                "try to refill the output buffer and send it"
                obs = self.ac_out_buffer_size
                if (len (self.ac_out_buffer) < obs):
                        while self.ac_refill_buffer ():
                                pass
        
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
                                #assert None == self.log (
                                #        'handle-write'
                                #        ' sent="%d" buffered="%d"' % (
                                #                sent, len (self.ac_out_buffer)
                                #                ),
                                #        'debug'
                                #        )
                        
        # Allow to use simplified or more sophisticated collector and producer
        # interfaces (like a netstring channel) or implementations (like a C
        # version of the original ;-).

        ac_consume_buffer = consume_buffer

        ac_refill_buffer = refill_buffer
        
        def push (self, p):
                "push a string or producer on the output queue, initiate send"
                assert type (p) == types.StringType or hasattr (p, 'more')
                self.producer_fifo.append (p)
                self.handle_write ()

        def close_when_done (self):
                """automatically close this channel once the outgoing queue 
                is empty"""
                if len (self.producer_fifo) == 0:
                        self.handle_close ()
                        #
                        # appending None to the producer_fifo when it is
                        # empty cause a subtle bug in readable_for_stall,
                        # and anyway, "when done" is now :-)
                else:
                        self.producer_fifo.append (None)

        # The Async_chat Simplified Interface

        terminator = '\n'

        def set_terminator (self, term):
                self.terminator = term

        def get_terminator (self):
                return self.terminator

        def collect_incoming_data(self, data):
                assert None == self.log (data, 'collect-incoming-data')

        def found_terminator(self):
                assert None == self.log (
                        self.get_terminator (), 'found-terminator'
                        )

# Note about this implementation
#
# This is a refactored version of asynchat.py as found in Python 2.4, and
# modified as to support stallable producers, loginfo, finalization.
# Incidentaly, this implementation allways use collection.deque for output
# FIFO queues instead of a class wrapper, and the push () method actually
# does what it is supposed to do and pushes a string at the end that output
# queue, not a Simple_producer instance.
#
# Since Allegra is designed to spare developpers the joy of asyncore and
# asynchat API by providing them ready-made client, servers and peers for
# the major Internet protocols, there is no need to maintain backward 
# compatibily with the Standard Library.
#
# In the Python Standard Library, asynchat is intended to be articulated,
# to provide a base class from which to derive new implementation of a
# TCP chat-like protocol and possibly distinct types of FIFO. In Allegra,
# async_chat provides the root class of ready-made TCP client and servers for
# various application protocols. One obvious simpler way to handler asynchat's 
# FIFO queue and the strings pushed directly on to it makes a lot of
# sense for optimization, the only thing left to do when so much is built
# atop of an interface.
#
# The end result is a lighter, faster and yet marginally more general
# implementation that suites a wide range of asynchronous servers, clients 
# and peers developped on top of it.
#
# Flat is better than nested, according to Python's zen. Practically it is
# indeed, because flat data structures are faster to instanciate and manage
# than nested trees for the CPython VM (a lot faster as the reverse evidence
# displayed by the outstanding performance gain of cElementTree demonstrates).
# And when developping from the prompt, a short hierarchy of flat name space
# are more usefull than a deeply nested and therefore usually dispersed name
# graph.
#
# For instance, Twisted original package maze and the confusion it provoked
# forced its author to a partial rewrite of a whole part of the API but
# without beeing able to get rid of the most problematic of the library
# itself: it is very difficult to read. And even more difficult to inspect
# from the prompt.
#
# Consider now Allegra's allmost flat name space (saves obvious functions
# best kept in and accessed from a separate module, possibly on their way
# to profiling and C optimization). All methods and properties of an HTTP
# client channel can be inspected without much transformation, because
# they are well named. A developper allways has a wide horizon of interfaces
# available, but in a single namespace: he see more of the state and can
# reaches more methods from it.
#