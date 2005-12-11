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


import exceptions, socket, sys, time, os

from errno import \
        EALREADY, EINPROGRESS, EWOULDBLOCK, ECONNRESET, \
        ENOTCONN, ESHUTDOWN, EINTR, EISCONN

from allegra import loginfo, async_loop, finalization


class Async_dispatcher (loginfo.Loginfo, finalization.Finalization):
    
        connected = accepting = closing = 0

        addr = None

        def __init__ (self, sock=None):
                if sock:
                        self.set_socket (sock)
                        # I think it should inherit this anyway
                        self.socket.setblocking (0)
                        self.connected = 1
                        # Does the constructor require that the socket
                        # passed be connected?
                        try:
                                self.addr = sock.getpeername ()
                        except socket.error:
                                # The addr isn't crucial
                                pass
                else:
                        self.socket = None

        def __repr__ (self):
                'async-dispatcher id="%x"' % id (self)

        def finalization (self, finalized):
                assert None == self.log ('finalized', 'debug')

        def add_channel (self):
                "add the dispatcher to the asynchronous I/O map"
                async_loop.async_map[self._fileno] = self

        def del_channel (self):
                "removes the dispatcher from the asynchronous I/O map"
                fd = self._fileno
                if async_loop.async_map.has_key (fd):
                        del async_loop.async_map[fd]

        def create_socket (self, family, type):
                "create a socket and add the dispatcher to the I/O map"
                self.family_and_type = family, type
                self.socket = socket.socket (family, type)
                self.socket.setblocking (0)
                self._fileno = self.socket.fileno ()
                self.add_channel ()

        def set_socket (self, sock):
                "set the dispatcher's socket and add itself to the I/O map"
                self.socket = sock
                self._fileno = sock.fileno()
                self.add_channel ()

        def set_reuse_addr (self):
                "try to re-use a server port if possible"
                try:
                        self.socket.setsockopt (
                                socket.SOL_SOCKET, 
                                socket.SO_REUSEADDR,
                                self.socket.getsockopt (
                                        socket.SOL_SOCKET, 
                                        socket.SO_REUSEADDR
                                        ) | 1
                                )
                except socket.error:
                        pass

        def readable (self):
                "predicate for inclusion as readable in the poll loop"
                return 1

        if os.name == 'mac':
                # The macintosh will select a listening socket for
                # write if you let it.  What might this mean?
                def writable (self):
                        "predicate for inclusion as writable in the poll loop"
                        return not self.accepting
                        
        else:
                def writable (self):
                        "predicate for inclusion as writable in the poll loop"
                        return 1

        # socket object methods.

        def listen (self, num):
                "listen and set the dispatcher's accepting state"
                self.accepting = 1
                if os.name == 'nt' and num > 5:
                        num = 1
                return self.socket.listen (num)

        def bind (self, addr):
                "bind to addr and set the dispatcher's addr property"
                self.addr = addr
                return self.socket.bind (addr)

        def connect (self, address):
                "try to connect and set the dispatcher's connected state"
                self.connected = 0
                err = self.socket.connect_ex (address)
                if err in (EINPROGRESS, EALREADY, EWOULDBLOCK):
                        return
                        
                if err in (0, EISCONN):
                        self.addr = address
                        self.connected = 1
                        self.handle_connect ()
                else:
                        raise socket.error, err

        def accept (self):
                "try to accept a connection"
                try:
                        conn, addr = self.socket.accept()
                        return conn, addr
                        
                except socket.error, why:
                        if why[0] == EWOULDBLOCK:
                                pass
                        else:
                                raise socket.error, why

        def send (self, data):
                "try to send data through the socket"
                try:
                        result = self.socket.send (data)
                        return result
                        
                except socket.error, why:
                        if why[0] == EWOULDBLOCK:
                                return 0
                                
                        else:
                                raise socket.error, why
                                
                        return 0

        def recv (self, buffer_size):
                "try to receive buffer_size bytes through the socket"
                try:
                        data = self.socket.recv (buffer_size)
                        if not data:
                                # a closed connection is indicated by signaling
                                # a read condition, and having recv() return 0.
                                self.handle_close()
                                return ''
                                
                        else:
                                return data
                        
                except MemoryError:    
                        # according to Sam Rushing, this is a place where
                        # MemoryError tend to be raised by Medusa. the rational 
                        # is that under high load, like a DDoS (or the /.
                        # effect :-), recv is the function that will be called 
                        # most *and* allocate the more memory.
                        #
                        sys.exit ("Out of Memory!") # do not even try to log!
                        
                except socket.error, why:
                        # winsock sometimes throws ENOTCONN
                        if why[0] in [ECONNRESET, ENOTCONN, ESHUTDOWN]:
                                self.handle_close()
                                return ''
                                
                        else:
                                raise socket.error, why

        def close (self):
                "remove the dispatcher from the I/O map and close the socket"
                self.del_channel ()
                self.socket.close ()
                #
                self.connected = 0
                self.closing = 1
                #
                # added here because a closed channel state may be accessed
                # by a scheduled event like a too-late timeout!

        def handle_read_event (self):
                "articulate read event as accept, connect or read."
                if self.accepting:
                        # for an accepting socket, getting a read implies
                        # that we are connected
                        if not self.connected:
                                self.connected = 1
                        self.handle_accept ()
                elif not self.connected:
                        self.handle_connect ()
                        self.connected = 1
                        self.handle_read ()
                else:
                        self.handle_read ()

        def handle_write_event (self):
                "articulate write event as connect or write."
                # getting a write implies that we are connected
                if not self.connected:
                        self.handle_connect ()
                        self.connected = 1
                self.handle_write ()

        def handle_error (self):
                "log a traceback and send a close event to the dispatcher"
                t, v = sys.exc_info ()[:2]
                if t is SystemExit:
                        raise t, v

                self.loginfo_traceback ()
                self.handle_close ()

        def handle_close (self):
                "assert debug log and close the dispatcher"
                assert None == self.log ('close', 'debug')
                self.close()

        def handle_read (self):
                assert None == self.log ('unhandled read event', 'debug')

        def handle_write (self):
                assert None == self.log ('unhandled write event', 'debug')

        def handle_connect (self):
                assert None == self.log ('unhandled connect event', 'debug')

        def handle_accept (self):
                assert None == self.log ('unhandled accept event', 'debug')


# Asynchronous File I/O: UNIX pipe and stdio only
#
# What follows is the original comments by Sam Rushing:
#
# After a little research (reading man pages on various unixen, and
# digging through the linux kernel), I've determined that select()
# isn't meant for doing doing asynchronous file i/o.
# Heartening, though - reading linux/mm/filemap.c shows that linux
# supports asynchronous read-ahead.  So _MOST_ of the time, the data
# will be sitting in memory for us already when we go to read it.
#
# What other OS's (besides NT) support async file i/o?  [VMS?]
#
# Regardless, this is useful for pipes, and stdin/stdout...

if os.name == 'posix':
        import fcntl

        class Async_file_wrapper:

                "wrap a file to with enough of a socket like interface"

                def __init__ (self, fd):
                        self.fd = fd
        
                def recv (self, *args):
                        return apply (os.read, (self.fd, ) + args)
        
                def send (self, *args):
                        return apply (os.write, (self.fd, ) + args)
        
                read = recv
                write = send
        
                def close (self):
                        return os.close (self.fd)
        
                def fileno (self):
                        return self.fd
                        

        class Async_file (Async_dispatcher):
                
                "An asyncore dispatcher for UNIX pipe and stdandard I/O."
                
                def __init__ (self, fd):
                        Async_dispatcher.__init__ (self)
                        self.connected = 1
                        # set it to non-blocking mode
                        flags = fcntl.fcntl (fd, fcntl.F_GETFL, 0)
                        flags = flags | os.O_NONBLOCK
                        fcntl.fcntl (fd, fcntl.F_SETFL, flags)
                        self.set_file (fd)
        
                def set_file (self, fd):
                        self._fileno = fd
                        self.socket = Async_file_wrapper (fd)
                        self.add_channel ()


# Note about this implementation
#
# This is a refactored version of the asyncore's original dispatcher class,
# with a new logging facility (loginfo). The poll functions and the
# asynchronous loop have been moved to async_loop, in a single module that
# integrates a non-blocking I/O loop, a heapq scheduler loop and a loop
# through a deque of finalizations.
#
# The two significant changes from the Standard Library version of asyncore
# are a more powerfull netstring/outlines logging facility and
#