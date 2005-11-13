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

import errno, time, collections, heapq

from allegra import loginfo


async_Exception = KeyboardInterrupt


# The socket map, a dictionnary of dispatchers indexed by their socket fileno

async_map = {}

def async_close ():
	for dispatcher in async_map.values ():
		dispatcher.close ()


# The original asyncore functions to poll this socket map for I/O

def poll1 (map, timeout=0.0):
        r = []; w = []; e = []
        for fd, obj in map.items ():
                if obj.readable ():
                        r.append (fd)
                if obj.writable ():
                        w.append (fd)
        if [] == r == w == e:
                time.sleep (timeout)
        else:
                try:
                        r, w, e = select.select (r, w, e, timeout)
                except ValueError:
                	# Default limit set to 512 in _select.pyd, no upper
                	# bound for NT, something in the many thousands for
                	# Linux. Anyway, this will not prevent a peer to
                	# handle many more sockets, provided no more than
                	# 512 of them are readable or writable concurrently.
                	#
                	loginfo.log ('select read="%d" write="%d"' % (
                		len (r), len (w)
                		), 'fatal')
                	raise async_Exception, 'select-fatal'
                	
                except select.error, err:
                        if err[0] != errno.EINTR:
                            raise
                            
                        else:
                            return

        for fd in r:
                try:
                        obj = map[fd]
                except KeyError:
                        continue

                try:
                        obj.handle_read_event ()
                except async_Exception:
                        raise async_Exception
                        
                except:
                        obj.handle_error ()

        for fd in w:
                try:
                        obj = map[fd]
                except KeyError:
                        continue

                try:
                        obj.handle_write_event ()
                except async_Exception:
                        raise async_Exception 
                        
                except:
                        obj.handle_error ()


def poll2 (map, timeout=0.0):
        # import poll
        timeout = int (timeout*1000) # timeout is in milliseconds
        l = []
        for fd, obj in map.items ():
                flags = 0
                if obj.readable ():
                        flags = poll.POLLIN
                if obj.writable ():
                        flags = flags | poll.POLLOUT
                if flags:
                        l.append ((fd, flags))
        r = poll.poll (l, timeout)
        for fd, flags in r:
                try:
                        obj = map[fd]
                except KeyError:
                        continue

                try:
                        if (flags  & poll.POLLIN):
                                obj.handle_read_event()
                        if (flags & poll.POLLOUT):
                                obj.handle_write_event()
                except async_Exception:
                        raise async_Exception 
                        
                except:
                        obj.handle_error ()


def poll3 (map, timeout=0.0):
        # Use the poll() support added to the select module in Python 2.0
        timeout = int (timeout*1000)
        pollster = select.poll ()
        for fd, obj in map.items():
                flags = 0
                if obj.readable ():
                        flags = select.POLLIN
                if obj.writable ():
                        flags = flags | select.POLLOUT
                if flags:
                        pollster.register (fd, flags)
        try:
                r = pollster.poll (timeout)
        except select.error, err:
                if err[0] != errno.EINTR:
                        raise
                        
                r = []
        for fd, flags in r:
                try:
                        obj = map[fd]
                except KeyError:
                        continue

                try:
                        if (flags  & select.POLLIN):
                                obj.handle_read_event()
                        if (flags & select.POLLOUT):
                                obj.handle_write_event()
                except async_Exception:
                        raise async_Exception 
                        
                except:
                        obj.handle_error()


# Select the best poll function available for this system

try:
	import poll
except:
	import select
	if hasattr (select, 'poll'):
		async_poll = poll3
	else:
		async_poll = poll1
else:
	async_poll = poll2

async_timeout = 0.1 # default to a much smaller interval (300) than asyncore


# Finalizations, the Garbage Collector asynchronous loop

async_finalized = collections.deque ()

def async_finalize ():
	"call all finalization queued"
	while True:
		try:
			finalize, finalized = async_finalized.popleft ()
		except IndexError:
			break
			
		try:
			finalize (finalized)
		except:
			loginfo.loginfo_traceback ()
	
	
# Scheduled Events

async_scheduled = []

def async_schedule (when, defered):
	"schedule a call to defered for when"
	heapq.heappush (async_scheduled, (when, defered))
	
def async_clock ():
	"call all defered scheduled after now"
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


# The async_Exception catcher

def async_catch ():
	"catch or throw an async_Exception"
	assert None == loginfo.log ('async_catch', 'debug')
	return False


# And finally, the loop itself

def loop ():
	"the asynchronous loop: poll, clock and finalize"
	assert None == loginfo.log ('async_loop_start', 'debug')
	while async_map:
		try:
			async_poll (async_map, async_timeout)
		except async_Exception:
			if not async_catch ():
				break
			
		async_clock () 
		async_finalize ()
	assert None == loginfo.log ('async_loop_stop', 'debug')


# Note about this implementation
#
# A marginaly extended and simplified asyncore loop
#
# Expanding to more asynchronous event stacks is not a "good thing" IMHO, 
# and certainly not to integrated peer networking with a GUI. This simple
# loop is implemented as a module (and not a class) because there is little
# practical use for two asynchronous loops in the same CPython VM. 
#
# Use two distinct processes instead ;-)
#
#
# One async_map only!
#
# It makes no practical sense to have more than one async_map index of
# channels to poll, because having more than one implies either that
# you reached the limit of the underlying system interface (and probably
# should use something else, like epoll events on Linux) or that you
# need more CPU time. In the latter case, what you should do is distribute
# the infrastructure, not complicate the network peer architecture.
#
#
# Performances
#
# However slow this Python code is, most of the implementation it integrates
# is made of fast C code from the CPython standard modules: gc, socket 
# or poll, collections and heapq. The core of Allegra is made of Python but
# most of the high profile functions integrated are functions from the standard 
# C modules or the CPython VM (which means that they are thread-safe and
# release the GIL, allowing them to be threaded by the system and not like
# Python bytecode simply juggled by the VM).
#
# Finalizations are implemented by the CPython VM as the __delete__ method, 
# asynchronously managed by its GC and queued in a collections.deque. The 
# scheduler is a simple application of a heap queue, and again most of the 
# implementation is in the standard heapq CPython module. Finally, the poll
# or select loops are just thin glue around the respective C system calls.
#
# The trade-off here is that even if an Allegra peer is significantly 
# slower at handling the HTTP protocol than an Apache server or a Java 
# Application Server, it will never be as slow as to loose the benefit
# of asynchrony: no synchronization chore and cost, no thread/process
# core and cost and a lot more memory available for cache.
#
# Last but not least, a network application peer does not have to scale
# much beyond the lower limits set on the select or poll call by most
# OS. An application peer handling 512 concurrent connections
#
# Foundation for a P2EE Stack?
#
# However, very much like a NET or J2EE stack, an Allegra peer can host
# network applications and enforce enough protection against the hosted
# applications' defects. Actually, the CPython VM provides most of that
# safety because it is an strong-typed but late-binding interpreter, one
# that makes it virtually impossible to "crash" (buffer overflow, broken
# C libraries interfaces, etc ...)
#
# What about malicious or broken access to Allegra's core API?
#
# Well, what about auditing the code hosted? What about testing it first
# and reading it one last time before putting it into production? C# or
# Java are not safer, actually there is in their API enough rope to hang
# both application servers from inside. Whatever the host, it makes more
# sense to audit the code deployed rather than restrict the API available.
# 
# And when it comes to source audit, Python is definitively more effective
# than Java or C#, because the same algorithm is usually shorter in Python.
#
# So, a CPython VM running an asynchronous peer like Allegra might very
# well prove to be a more competitive solution than Sun's or the
# Microsoft's frameworks.