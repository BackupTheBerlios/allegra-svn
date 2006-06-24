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

import select, errno, collections

from allegra import loginfo, async_loop, async_core
        
        
def async_concurrent (new, writable, readable, stalled, limit):
        #
        # this is the nearly O(1) part of the async_c10k loop
        #
        n = new.items ()[:limit]
        rest = max (0, limit - len (new))
        if rest > 0:
                w = writable.items ()[:rest]
                rest = max (0, rest - len (w))
                if rest > 0:
                        r = readable.items ()[:rest]
                        rest = max (0, rest - len (r))
                        if rest > 0:
                                return (n, w, r, stalled.items ()[:rest])
        
                        return (n, w, r, ())
        
                return (n, w, (), ())

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
        if len (w) > limit:
                w = w[:limit]
        if len (r) > limit:
                r = r[:limit]
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
                        raise async_Exception
                        
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
                        raise async_Exception 
                        
                except:
                        dispatcher.handle_error ()


def async_poll (
        map, timeout, new, writable, readable, stalled, limit
        ):
        nd, wd, rd, sd = async_concurrent (
                new, writable, readable, stalled, limit
                )
        timeout = int (timeout*1000)
        pollster = select.poll ()
        for fd, dispatcher in nd:
                if dispatcher.writable ():
                        writable[fd] = new.pop (fd)
                        if dispatcher.readable ():
                                pollster.register (fd, (
                                        select.POLLOUT | 
                                        select.POLLIN | 
                                        select.POLLPRI
                                        ))
                        else:
                                pollster.register (fd, select.POLLOUT)
                elif dispatcher.readable ():
                        readable[fd] = new.pop (fd)
                        pollster.register (
                                fd, select.POLLIN | select.POLLPRI
                                )
                else:
                        stalled[fd] = new.pop (fd)
        for fd, dispatcher in wd:
                if dispatcher.writable ():
                        if dispatcher.readable ():
                                pollster.register (fd, (
                                        select.POLLOUT | 
                                        select.POLLIN | 
                                        select.POLLPRI
                                        ))
                        else:
                                pollster.register (fd, select.POLLOUT)
                elif dispatcher.readable ():
                        readable[fd] = writable.pop (fd)
                        pollster.register (
                                fd, select.POLLIN | select.POLLPRI
                                )
                else:
                        stalled[fd] = writable.pop (fd)
        for fd, dispatcher in rd:
                if dispatcher.writable ():
                        writable[fd] = readable.pop (fd)
                        if dispatcher.readable ():
                                pollster.register (fd, (
                                        select.POLLOUT | 
                                        select.POLLIN | 
                                        select.POLLPRI
                                        ))
                        else:
                                pollster.register (fd, select.POLLOUT)
                elif dispatcher.readable ():
                        pollster.register (
                                fd, select.POLLIN | select.POLLPRI
                                )
                else:
                        stalled[fd] = readable.pop (fd)
        for fd, dispatcher in sd:
                if dispatcher.writable ():
                        writable[fd] = stalled.pop (fd)
                        if dispatcher.readable ():
                                pollster.register (fd, (
                                        select.POLLOUT | 
                                        select.POLLIN | 
                                        select.POLLPRI
                                        ))
                        else:
                                pollster.register (fd, select.POLLOUT)
                elif dispatcher.readable ():
                        readable[fd] = stalled.pop (fd)
                        pollster.register (
                                fd, select.POLLIN | select.POLLPRI
                                )
        try:
                p = pollster.poll (timeout)
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
                                if flags & (select.POLLIN | select.POLLPRI):
                                        dispatcher.handle_read_event()
                                if flags & select.POLLOUT:
                                        dispatcher.handle_write_event()
                        except async_Exception:
                                raise async_Exception 
                                
                        except:
                                dispatcher.handle_error()
        
        
if hasattr (select, 'poll'):
        async_io_c10k = async_poll
else:
        async_io_c10k = async_select
           
                        
# decorate async_loop.async_io 

new = {}
writable = {}
readable = {}
stalled = {}

# decorate async_core.Dispatcher

async_core.Dispatcher.async_new = new 

def add_channel (dispatcher):
        fd = dispatcher._fileno
        dispatcher.async_map[fd] = dispatcher.async_new[fd] = dispatcher

async_core.Dispatcher.add_channel = add_channel

async_core.Dispatcher.async_writable = writable
async_core.Dispatcher.async_readable = readable
async_core.Dispatcher.async_stalled = stalled

def del_channel (dispatcher):
        fd = dispatcher._fileno
        del dispatcher.async_map[fd]
        try:
                del dispatcher.async_readable[fd]
        except KeyError:
                try:
                        del dispatcher.async_writable[fd]
                except KeyError:
                        del dispatcher.async_stalled[fd]
                
async_core.Dispatcher.del_channel = del_channel

def concurrency (limit):
        def async_io (map, timeout):
                async_io_c10k (
                        map, timeout, 
                        new, writable, readable, stalled, limit
                        )
        
        async_loop.async_io = async_io


"""An Event-like I/O poll loop

The async_c10k.async_io functions test a maximum number of dispatcher 
for readability and writability, then poll I/O for the readable 
and/or writable associated file descriptors, using two maps: first 
the one of previously writable dispatchers and second the one of 
previously readable or stalled dispatchers.

Previously writable sockets are polled first, eventually moved to
the readable map when their status change, when no more output is
available. Since input and output are interleaving, the loop acts 
like a revolving door between the maps, moving to high priority
the connections with a response, moving to low priority the 
dispatchers waiting for input. 

When the number of writable connections is above the limit, the
peer won't poll dispatcher waiting for input, slowing down the
number of connections submitting requests, which is a good thing.
 
When the number of writable connections is below the limit, the 
peer will poll I/O for readable dispatchers too. So, the application 
will only read more input if it is not saturating its output, which
implies a smoother behaviour, less buffering and load taken at once
and which are stressing the computer system (yielding a general decrease
in operating performances).

This loop will stall under only one condition: that enough writable
connections below the concurrency limit have stalled output. 

Practically this imply a lot of zombie TCP peer requesting data never 
read ... or a dead network. In the case of a dead network, stalling is 
actually a very good behaviour. As for zombies, they must be taken care 
of by thigh connection management: only an audit can counter inadvertent
and malicious deniers of service.

However, for buffered async_net and async_chat connections, zombie 
connections will either not be writable because there is not output
queued (a spleeping HTTP/1.1 pipeline) because their buffers are filled
and not emptyied.

"""

