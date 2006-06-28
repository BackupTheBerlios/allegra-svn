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

"http://laurentszyster.be/blog/async10k/"

import select, errno, asyncore


async_Exception = asyncore.ExitNow


def async_concurrent (new, writable, readable, stalled, limit):
        #
        # this is the nearly O(1) part of the async10k loop
        #
        n = new.items ()[:limit]
        rest = limit - len (new)
        if rest > 0:
                w = writable.items ()[:rest]
                rest = rest - len (w)
                if rest > 0:
                        r = readable.items ()[:rest]
                        rest = rest - len (r)
                        if rest > 0:
                                return (n, w, r, stalled.items ()[:rest])
        
                        return (n, w, r, ())
        
                return (n, w, (), ())
        
        return (n, (), (), ())


def async_select (
        map, timeout, new, writable, readable, stalled, limit
        ):
        nd, wd, rd, sd = async_concurrent (
                new, writable, readable, stalled, limit
                )
        #
        # and here is the O(N) part, where N < limit ...
        #
        r = []
        for fd, dispatcher in nd:
                if dispatcher.writable ():
                        writable[fd] = new.pop (fd)
                        if dispatcher.readable ():
                                r.append (fd)
                elif dispatcher.readable ():
                        readable[fd] = new.pop (fd)
                        r.append (fd)
                else:
                        stalled[fd] = new.pop (fd)
        for fd, dispatcher in wd:
                if dispatcher.writable ():
                        if dispatcher.readable ():
                                r.append (fd)
                elif dispatcher.readable ():
                        readable[fd] = writable.pop (fd)
                        r.append (fd)
                else:
                        stalled[fd] = writable.pop (fd)
        for fd, dispatcher in rd:
                if dispatcher.writable ():
                        writable[fd] = readable.pop (fd)
                        if dispatcher.readable ():
                                r.append (fd)
                elif dispatcher.readable ():
                        r.append (fd)
                else:
                        stalled[fd] = readable.pop (fd)
        for fd, dispatcher in sd:
                if dispatcher.writable ():
                        writable[fd] = stalled.pop (fd)
                        if dispatcher.readable ():
                                r.append (fd)
                elif dispatcher.readable ():
                        readable[fd] = stalled.pop (fd)
                        r.append (fd)                
        if not (writable or r):
                time.sleep (timeout)
                return
        
        w = writable.keys () # probably faster than all those w.append (fd)
        try:
                r, w, e = select.select (r, w, [], timeout)
        except select.error, err:
                if err[0] != errno.EINTR:
                    raise
                    
                else:
                    return

        for fd in r:
                try:
                        dispatcher = map[fd]
                except KeyError:
                        continue
                        
                try:
                        dispatcher.handle_read_event ()
                except async_Exception:
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
                except async_Exception:
                        raise
                        
                except:
                        dispatcher.handle_error ()
        w = set (w)
        inactive = (w + set (r)) - (set (ww) + set (rr))
        if inactive:
                for fd in (inactive & w):
                        stalled[fd] = writable.pop (fd)
                for fd in (inactive - w):
                        stalled[fd] = readable.pop (fd)


def async_poll (
        map, timeout, new, writable, readable, stalled, limit
        ):
        "limit the connections tested and poll writable or readable only"
        # first limit in the order of priority
        #
        nd, wd, rd, sd = async_concurrent (
                new, writable, readable, stalled, limit
                )
        #
        # note that you can reload the select module.
        #
        pollster = select.poll ()
        W = select.POLLOUT
        R = select.POLLIN | select.POLLPRI
        RW = R | W
        #
        # now the four loops: new, writable, readable and stalled:
        #
        for fd, dispatcher in nd:
                if dispatcher.writable ():
                        writable[fd] = new.pop (fd)
                        if dispatcher.readable ():
                                pollster.register (fd, RW)
                        else:
                                pollster.register (fd, W)
                elif dispatcher.readable ():
                        readable[fd] = new.pop (fd)
                        pollster.register (R)
                else:
                        stalled[fd] = new.pop (fd)
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
        #
        # try to poll
        #
        try:
                p = pollster.poll (int (timeout*1000))
        except select.error, err:
                if err[0] != errno.EINTR:
                        raise

        else:
                # and handle I/O events and exceptions.
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
                                elif readable.has_key (fd):
                                        stalled[fd] = readable.pop (fd)
                                else:
                                        stalled[fd] = writable.pop (fd)
                        except async_Exception:
                                raise
                                
                        except:
                                dispatcher.handle_error()
        
        
if hasattr (select, 'poll'):
        async_io = async_poll
else:
        async_io = async_select
                   
                        
# decorate asyncore

new = {}
writable = {}
readable = {}
stalled = {}

def add_channel (dispatcher, map=None):
        fd = dispatcher._fileno
        dispatcher.async_map[fd] = dispatcher.async_new[fd] = dispatcher

def del_channel (dispatcher, map=None):
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
                                try:
                                        del dispatcher.async_stalled[fd]
                                except KeyError:
                                        del dispatcher.async_new[fd]
                

concurrency = 512

def poll_fun (timeout, map):
        async_io (
                map, timeout, 
                new, writable, readable, stalled, concurrency
                )

asyncore.poll_fun = poll_fun

Dispatcher = asyncore.dispatcher
Dispatcher.async_map = asyncore.socket_map
Dispatcher.async_new = new 
Dispatcher.async_writable = writable
Dispatcher.async_readable = readable
Dispatcher.async_stalled = stalled
Dispatcher.add_channel = add_channel
Dispatcher.del_channel = del_channel