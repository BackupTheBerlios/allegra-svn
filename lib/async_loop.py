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

async_catchers = []

def async_catch ():
        "call catchers on async_Exception (KeyboardInterrupt by default)"
        assert None == loginfo.log ('async_catch', 'debug')
        if not async_catchers:
                if __debug__:
                        for dispatcher in async_map:
                                loginfo.log (
                                        '%r' % dispatcher, 'undispatched'
                                        )
                        for scheduled in async_scheduled:
                                loginfo.log (
                                        '%r' % (scheduled, ), 'unscheduled'
                                        )
                        for finalized in async_finalized:
                                loginfo.log (
                                        '%r' % (finalized, ), 'unfinalized'
                                        )
                return False
        
        for catcher in tuple (async_catchers):
                if catcher ():
                        async_catchers.remove (catcher)
        return len (async_catchers) > 0


# Application Programming Interfaces

def schedule (when, defered):
        "schedule a call to defered for when"
        heapq.heappush (async_scheduled, (when, defered))        
        

def catch (catcher):
        async_catchers.append (catcher)


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
   
        

# Schedule
#
# Having now peaked at both twisted, ACE and the libevent interfaces, I can
# proudly say that the async_loop.schedule and the timeouts.Timeouts
# interfaces are better.
#
# Allegra offers three kind of time events: single events defered at a fixed 
# interval of time (ie the classic timeout) and single or recurent events 
# scheduled at varying interval.
#
# The async_schedule interface has one or two advantages over the
# competing designs. First it provides a way to schedule recurrent events 
# without some ugly callback, without pegging the heap queue of the event 
# "clock" implementation, and with an interface that prove to be quite 
# flexible and simple for general purpose applications (like zombie channel
# scavenging, TPC server or UDP peer gracefull shutdown, etc ...).
#
# Second, it allows to schedule events at absolute point in time and provide
# a very much usefull absolute scheduled time value to its handler. Moreover
# the underlying implementation implies that time is stable, that the
# scheduled event's notion of time does not drift even if polling time is
# done with little precision.
#
#
