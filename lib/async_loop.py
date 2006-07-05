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

"http://laurentszyster.be/blog/async_loop/"

import select, errno, time, collections, heapq

from allegra import loginfo


Exit = KeyboardInterrupt


# Poll I/O

def _io_select (map, timeout, limit):
        "poll for I/O a limited number of writable/readable dispatchers"
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


def _io_poll (map, timeout, limit):
        "poll for I/O a limited number of writable/readable dispatchers"
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
                        except Exit:
                                raise 
                                
                        except:
                                dispatcher.handle_error()


# select the best I/O poll function available for this system

if hasattr (select, 'poll'):
	_io = _io_poll
else:
	_io = _io_select


# Poll Memory (Finalizations, ie: CPython __del__ decoupled)

_finalized = collections.deque ()

def _finalize ():
	"call all finalizations queued"
        while True:
                try:
                        finalized = _finalized.popleft ()
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

_scheduled = []

def _clock ():
	"call all events scheduled before now"
	now = time.time ()
	while _scheduled:
		# get the next defered ...
		event = heapq.heappop (_scheduled)
		if event[0] > now:
			heapq.heappush (_scheduled, event)
			break  # ... nothing to defer now.

		try:
			# ... do defer and ...
			continued = event[1] (event[0])
		except:
			loginfo.loginfo_traceback ()
		else:
			if continued != None:
				heapq.heappush (_scheduled, continued) 
				#
				# ... maybe continue ...


# Poll Signals (Exceptions Handler)

_catchers = []

def _catched ():
        "call catchers on Exit exception"
        assert None == loginfo.log ('async_catch', 'debug')
        if _catchers:
                for catcher in tuple (_catchers):
                        if catcher ():
                                _catchers.remove (catcher)
                return True
        
        if __debug__:
                for dispatcher in _dispatched:
                        loginfo.log (
                                '%r' % dispatcher, 'undispatched'
                                )
                for event in _scheduled:
                        loginfo.log (
                                '%r' % (event, ), 'unscheduled'
                                )
                for finalized in _finalized:
                        loginfo.log (
                                '%r' % (finalized, ), 'unfinalized'
                                )
        return False


# Application Programming Interfaces

def schedule (when, scheduled):
        "schedule a call to scheduled after when"
        heapq.heappush (_scheduled, (when, scheduled))        
        

def catch (catcher):
        "register an catcher for the Exit exception"
        _catchers.append (catcher)


concurrency = 512
precision = 0.1

_dispatched = {}

def dispatch ():
        "dispatch I/O, time and finalization events"
        assert None == loginfo.log ('async_dispatch_start', 'debug')
        while _dispatched or _scheduled or _finalized:
                try:
                        _io (_dispatched, precision, concurrency)
                        _clock ()
                        _finalize ()
                except Exit:
                        if not _catched ():
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
