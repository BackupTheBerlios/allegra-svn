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

"""A marginally extended async loop implementation, with finalizations 
and scheduled events. Cheap asynchronous continuations are provided by a 
piggy-back of the CPython GC and the simplest event scheduler possible is
implemented as a heap queue."""

import select, errno, time, collections, heapq

from allegra import loginfo


async_Exception = KeyboardInterrupt


# Variables

concurrency = 512
async_timeout = 0.1 # default to a much smaller interval (300) than asyncore

async_map = {}
async_scheduled = []
async_finalized = collections.deque ()


# Poll Functions, starting with I/O

def async_io_select (map, timeout, limit):
        r = []
        w = []
        concurrent = map.items ()
        if len (concurrent) > limit:
                concurrent = concurrent[:limit]
        for fd, dispatcher in concurrent:
                if dispatcher.readable ():
                        r.append (fd)
                if dispatcher.writable ():
                        w.append (fd)
        if len (r) + len (w) == 0:
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


def async_io_poll (map, timeout, limit):
        timeout = int (timeout*1000)
        pollster = select.poll ()
        R = select.POLLIN | select.POLLPRI
        W = select.POLLOUT
        RW = R | W
        concurrent = map.items ()
        if len (concurrent) > limit:
                concurrent = concurrent[:limit]
        for fd, dispatcher in concurrent:
                if dispatcher.readable ():
                        if dispatcher.writable ():
                                pollster.register (fd, RW)
                        else:
                                pollster.register (fd, R)
                elif dispatcher.writable ():
                        pollster.register (fd, W)
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
                                if flags & R:
                                        dispatcher.handle_read_event ()
                                if flags & W:
                                        dispatcher.handle_write_event ()
                        except async_Exception:
                                raise async_Exception 
                                
                        except:
                                dispatcher.handle_error()


# Select the best I/O poll function available for this system

if hasattr (select, 'poll'):
	async_io = async_io_poll
else:
	async_io = async_io_select


# Poll Memory (Finalizations, ie: CPython Garbage Collection decoupled)

def async_finalize ():
	"call all finalization queued"
        while True:
                try:
                        finalized = async_finalized.popleft ()
                except IndexError:
                        break
                       
                try:
                        finalized.finalization = finalized.finalization (
                               finalized
                               ) # finalize and maybe continue ...
                except:
                        finalized.finalization = None
                        loginfo.loginfo_traceback () # log exception
        
	
# Poll Time (Scheduled Events)

def async_clock ():
	"call all defered scheduled before now"
	if not async_scheduled:
		return
		
	now = time.time ()
	while async_scheduled:
		# get the next defered ...
		defered = heapq.heappop (async_scheduled)
		if defered[0] > now:
			heapq.heappush (async_scheduled, defered)
			break  # ... nothing to defer now.

		try:
			# ... do defer and ...
			defered = defered[1] (defered[0])
		except:
			loginfo.loginfo_traceback ()
		else:
			if defered != None:
				heapq.heappush (async_scheduled, defered) 
				#
				# ... maybe continue ...


# Poll Signals (Exceptions Handler)

def async_catch ():
	"throw an async_Exception"
	assert None == loginfo.log ('async_catch', 'debug')
	return False


# The Push Function(s)

def schedule (when, defered):
        "schedule a call to defered for when"
        heapq.heappush (async_scheduled, (when, defered))        

async_schedule = schedule # TODO: move to a simpler namespace
        

# The loop Itself

def dispatch ():
        "poll, clock and finalize while there is at least one event"
        assert None == loginfo.log ('async_dispatch_start', 'debug')
        while async_map or async_scheduled or async_finalized:
                try:
                        async_io (async_map, async_timeout, concurrency)
                        async_clock ()
                        async_finalize ()
                except async_Exception:
                        if not async_catch ():
                                break
                
                except:
                        loginfo.loginfo_traceback ()
        
        assert None == loginfo.log ('async_dispatch_stop', 'debug')
   
        
# TODO: move to a simpler and yet more powerfull signal catching interface
#
# catcher (signal) == False | True
#
# async_loop.async_catchers = []
# async_loop.async_catch (signal) == False | True
# async_loop.catch (catcher)
#

async_catchers2 = []

def async_catch2 ():
        "call catchers on async_Exception (KeyboardInterrupt by default)"
        if not async_catchers2:
                return False
        
        for catcher in tuple (async_catchers2):
                if catcher ():
                        async_catchers2.remove (catcher)
        return True

def catch2 (catcher):
        async_catchers2.append (catcher)


