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

"""A marginally extended asyncore.loop implementation,, with finalizations 
and scheduled events. Cheap asynchronous continuations are provided by a 
piggy-back of the CPython GIL and the simplest event scheduler possible is
implemented as a heap queue (also a CPyton feature)."""

import gc, time, collections, heapq

from allegra import loginfo


try:
	import poll
except:
	import select
	if hasattr (select, 'poll'):
		from asyncore import poll3 as async_poll
	else:
		from asyncore import poll as async_poll
else:
	from asyncore import poll2 as async_poll

from asyncore import socket_map as async_map

async_timeout = 0.1


async_finalized = collections.deque ()

def async_finalize ():
	"collect garbage and call all finalization queued"
	garbage = gc.collect ()
	if garbage > 0:
		assert None == loginfo.log (
			'async_finalize garbage="%d" count="%d"' % (
				garbage, len (async_finalized)
				), 'debug'
			)
	while True:
		try:
			finalize = async_finalized.popleft ()
		except IndexError:
			break
			
		try:
			finalize ()
		except:
			loginfo.loginfo_traceback ()
	

async_scheduled = []

def async_schedule (when, defered):
	"schedule a call to defered for when"
	heapq.heappush (async_scheduled, (when, defered))
	
def async_clock ():
	"call all defered whose time have come"
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


async_Exception = KeyboardInterrupt

def async_catch ():
	"catch or throw an async_Exception"
	assert None == loginfo.log ('async_catch', 'debug')
	return False


def loop ():
	"the asynchronous loop: finalize, clock and poll; finaly finalize."
	assert None == loginfo.log ('async_loop_start', 'debug')
	gc.disable ()
	while async_map:
		async_finalize ()
		async_clock ()
		try:
			async_poll (async_timeout, async_map)
		except async_Exception:
			if not async_catch ():
				break
				
	async_finalize ()
	assert None == loginfo.log ('async_loop_stop', 'debug')
	#
	# drop any defered in the last async_poll loop, you should collect
	# them in async_scheduled at the exit of the loop. finalizations are
	# handled appropriately, after the async_poll, catching any finalized
	# that would result from the deletion of the last asynchronous data
	# structures.


# Note about this implementation
#
# A marginaly extended asyncore loop
#
# Expanding to more asynchronous event stacks is not a "good thing" IMHO, 
# and certainly not to integrated peer networking with a GUI. This simple
# loop is implemented as a module (and not a class) because there is little
# practical use for two asynchronous loops in the same CPython VM. 
#
# Use two distinct processes instead ;-)
