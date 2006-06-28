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


def async_concurrent (writable, readable, stalled, limit):
        w = writable.items ()[:limit]
        rest = limit - len (w)
        if rest > 0:
                r = readable.items ()[:rest]
                rest = rest - len (r)
                if rest > 0:
                        return w, r, stalled.items ()[:rest]

                return w, r, ()

        return w, (), ()


def async_select (
        map, timeout, writable, readable, stalled, limit
        ):
        wd, rd, sd = async_concurrent (
                writable, readable, stalled, limit
                )
        w = []
        r = []
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
        if not (writable or r):
                time.sleep (timeout)
                return
        
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
        #w = set (w)
        #inactive = (w + set (r)) - (set (ww) + set (rr))
        #if inactive:
        #        for fd in (inactive & w):
        #                stalled[fd] = writable.pop (fd)
        #        for fd in (inactive - w):
        #                stalled[fd] = readable.pop (fd)


def async_poll (
        map, timeout, writable, readable, stalled, limit
        ):
        "limit the connections tested and poll writable or readable only"
        # first limit in the order of priority
        #
        wd, rd, sd = async_concurrent (
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
                                #else:
                                #        stalled[fd] = writable.pop (fd)
                        except async_Exception:
                                raise
                                
                        except:
                                dispatcher.handle_error()
        
        
if hasattr (select, 'poll'):
        async_io = async_poll
else:
        async_io = async_select
                   
                        
# decorate asyncore

async_writable = {}
async_readable = {}
async_stalled = {}

def add_channel (dispatcher, map=None):
        fd = dispatcher._fileno
        dispatcher.async_map[fd] = dispatcher.async_readable[fd] = dispatcher

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
                                del dispatcher.async_stalled[fd]
                

concurrency = 512

def poll_fun (timeout, map):
        async_io (
                map, timeout, 
                async_writable, async_readable, async_stalled, concurrency
                )

asyncore.poll_fun = poll_fun

Dispatcher = asyncore.dispatcher
Dispatcher.async_map = asyncore.socket_map
Dispatcher.async_writable = async_writable
Dispatcher.async_readable = async_readable
Dispatcher.async_stalled = async_stalled
Dispatcher.add_channel = add_channel
Dispatcher.del_channel = del_channel