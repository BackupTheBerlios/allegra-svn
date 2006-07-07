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

"http://laurentszyster.be/blog/async_c10k/"

import select, errno

# decorate async_loop._io

from allegra import async_loop


def _concurrent (limit, active, writable, readable, stalled):
        "limit by priority the number of dispatchers polled concurrently"
        a = active.items ()
        limit -= len (a)
        w = writable.items ()[:limit]
        limit -= len (w)
        if limit > 0:
                r = readable.items ()[:limit]
                limit -= len (r)
                if limit > 0:
                        s = stalled.items ()[:limit]
                        return a, w, r, s, (limit - len (s))

                return a, w, r, (), 0

        return a, w, (), (), 0

def _io_select_c10k (
        map, timeout, limit, active, writable, readable, stalled
        ):
        "poll for I/O a limited number of dispatchers, by priority"
        ad, wd, rd, sd, rest = _concurrent (
                limit, writable, readable, stalled
                )
        w = []
        r = []
        for fd, dispatcher in ad:
                if dispatcher.writable ():
                        w.append (fd)
                        if dispatcher.readable ():
                                r.append (fd)
                elif dispatcher.readable ():
                        r.append (fd)
        for fd, dispatcher in wd:
                if dispatcher.writable ():
                        w.append (fd)
                        if dispatcher.readable ():
                                r.append (fd)
                elif dispatcher.readable ():
                        readable[fd] = writable.pop (fd)
                        r.append (fd)
                else:
                        stalled[fd] = writable.pop (fd)
        for fd, dispatcher in rd:
                if dispatcher.writable ():
                        w.append (fd)
                        writable[fd] = readable.pop (fd)
                        if dispatcher.readable ():
                                r.append (fd)
                elif dispatcher.readable ():
                        r.append (fd)
                else:
                        stalled[fd] = readable.pop (fd)
        for fd, dispatcher in sd:
                if dispatcher.writable ():
                        w.append (fd)
                        writable[fd] = stalled.pop (fd)
                        if dispatcher.readable ():
                                r.append (fd)
                elif dispatcher.readable ():
                        readable[fd] = stalled.pop (fd)
                        r.append (fd)                
        if len (w) + len (r) == 0:
                time.sleep (timeout)
                return limit - rest, 0
        
        try:
                r, w, e = select.select (r, w, [], timeout)
        except select.error, err:
                if err[0] != errno.EINTR:
                    raise
                    
                else:
                    return limit - rest, 0

        for fd in r:
                try:
                        dispatcher = map[fd]
                except KeyError:
                        continue
                        
                try:
                        dispatcher.handle_read_event ()
                except Exit:
                        raise
                        
                except:
                        dispatcher.handle_error ()
        for fd in w:
                try:
                        dispatcher = map[fd]
                except KeyError:
                        continue
                        
                try:
                        dispatcher.handle_write_event ()
                except Exit:
                        raise
                        
                except:
                        dispatcher.handle_error ()
        #w = set (w)
        #inactive = (w + set (r)) - (set (ww) + set (rr))
        #if inactive:
        #        for fd in (inactive & w):
        #                stalled[fd] = writable.pop (fd)
        #        for fd in (inactive - w):
        #                stalled[fd] = readable.pop (fd)
        return limit - rest, len (w) + len (r)

def _io_poll_c10k (
        map, timeout, limit, active, writable, readable, stalled
        ):
        "poll for I/O a limited number of dispatchers, by priority"
        ad, wd, rd, sd, rest = _concurrent (
                limit, active, writable, readable, stalled
                )
        pollster = select.poll ()
        W = select.POLLOUT
        R = select.POLLIN | select.POLLPRI
        RW = R | W
        for fd, dispatcher in ad:
                if dispatcher.writable ():
                        if dispatcher.readable ():
                                pollster.register (fd, RW)
                        else:
                                pollster.register (fd, W)
                elif dispatcher.readable ():
                        pollster.register (R)
        for fd, dispatcher in wd:
                if dispatcher.writable ():
                        if dispatcher.readable ():
                                pollster.register (fd, RW)
                        else:
                                pollster.register (fd, W)
                elif dispatcher.readable ():
                        readable[fd] = writable.pop (fd)
                        pollster.register (R)
                else:
                        stalled[fd] = writable.pop (fd)
        for fd, dispatcher in rd:
                if dispatcher.writable ():
                        writable[fd] = readable.pop (fd)
                        if dispatcher.readable ():
                                pollster.register (fd, RW)
                        else:
                                pollster.register (fd, W)
                elif dispatcher.readable ():
                        pollster.register (R)
                else:
                        stalled[fd] = readable.pop (fd)
        for fd, dispatcher in sd:
                if dispatcher.writable ():
                        writable[fd] = stalled.pop (fd)
                        if dispatcher.readable ():
                                pollster.register (fd, RW)
                        else:
                                pollster.register (fd, W)
                elif dispatcher.readable ():
                        readable[fd] = stalled.pop (fd)
                        pollster.register (R)
        try:
                p = pollster.poll (int (timeout*1000))
        except select.error, err:
                if err[0] != errno.EINTR:
                        raise

        else:
                for fd, flags in p:
                        try:
                                dispatcher = map[fd]
                        except KeyError:
                                continue
                                
                        try:
                                if flags & R:
                                        dispatcher.handle_read_event()
                                        if flags & W:
                                                dispatcher.handle_write_event()
                                elif flags & W:
                                        dispatcher.handle_write_event()
                                #elif readable.has_key (fd):
                                #        stalled[fd] = readable.pop (fd)
                                #elif writable.has_key (fd):
                                #        stalled[fd] = writable.pop (fd)
                        except Exit:
                                raise
                                
                        except:
                                dispatcher.handle_error()
        return limit - rest, len (p)

if hasattr (select, 'poll'):
        _io_c10k = _io_poll_c10k
else:
        _io_c10k = _io_select_c10k
                   
_active = {}
_writable = {}
_readable = {}
_stalled = {}

def _io (map, timeout, limit):
        return _io_c10k (
                map, timeout, limit, 
                _active, _writable, _readable, _stalled
                )

async_loop._io = _io

# decorate async_core's Dispatcher

from allegra import async_core

Dispatcher = async_core.Dispatcher

Dispatcher.async_writable = _writable
Dispatcher.async_readable = _readable
Dispatcher.async_stalled = _stalled

def add_stallable (dispatcher):
        fd = dispatcher._fileno
        dispatcher.async_map[fd] = dispatcher.async_readable[fd] = dispatcher

Dispatcher.add_channel = add_stallable

def del_stallable (dispatcher):
        fd = dispatcher._fileno
        dispatcher._fileno = None
        try:
                del dispatcher.async_map[fd]
        except KeyError:
                pass
        else:
                try:
                        del dispatcher.async_readable[fd]
                except KeyError:
                        try:
                                del dispatcher.async_writable[fd]
                        except KeyError:
                                del dispatcher.async_stalled[fd]

Dispatcher.del_channel = del_stallable

# decorate the select_trigger.Trigger and async_server.Listen dispatchers

from allegra import select_trigger, async_server

def add_active (dispatcher):
        fd = dispatcher._fileno
        assert len (dispatcher.async_active[fd]) < async_loop.concurrency
        dispatcher.async_map[fd] = dispatcher.async_active[fd] = dispatcher

def del_active (dispatcher):
        fd = dispatcher._fileno
        dispatcher._fileno = None
        try:
                del dispatcher.async_map[fd]
        except KeyError:
                pass
        else:
                del dispatcher.async_active[fd]

for Dispatcher in (select_trigger.Trigger, async_server.Listen):
        Dispatcher.async_active = _active
        Dispatcher.add_channel = add_active
        Dispatcher.del_channel = del_active
        
del Dispatcher
                
# TODO: move from dictionnaries to pair of deques for the writable, readable
#       and stalled priority queues, actually queuing instead of hashing.
#       
#       the problem with dictionnaries is the possibility for a stalled
#       dispatcher to have a so high fileno that it will never be tested
#       again as long as there are more writable and readable dispatchers
#       below it than the concurrency limit, when new dispatchers get 
#       assigned lower fd numbers.