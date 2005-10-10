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

""

from allegra import loginfo


async_finalized = []

def async_immediate ():
	while async_finalized:
		try:
			async_finalized.pop (0) ()
		except:
			loginfo.loginfo_traceback ()
	

from time import time
from heapq import heappush, heappop

async_defered = []

def async_defer (when, defered):
	heappush (async_defered, (when, defered))
	
def async_clock ():
	now = time ()
	while async_defered:
		# get the next defered ...
		defered = heappop (async_defered)
		if defered[0] > now:
			heappush (async_defered, defered)
			break  # ... nothing to defer now.

		try:
			# ... do defer and ...
			defered = defered[1] (defered[0])
		except:
			loginfo.loginfo_traceback ()
		else:
			if defered != None:
				heappush (async_defered, defered) 
				#
				# ... maybe continue ...


async_timeout = 0.1

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

async_Exception = KeyboardInterrupt

def async_catch ():
	assert None == loginfo.log ('<async-catch/>', '')
	return

def loop ():
	assert None == loginfo.log ('<async-loop/>', '')
	while async_map:
		try:
			if async_finalized:
				async_immediate ()
			if async_defered:
				async_clock ()
			async_poll (async_timeout, async_map)
		except async_Exception:
			if not async_catch ():
				break
				
	if async_finalized:
		assert None == loginfo.log ('<async-loop-finalize/>', '')
		async_immediate ()
	#
	# drop any defered in the last async_poll loop, you should collect
	# them in async_defered at the exit of the loop. finalizations are
	# handled appropriately, after the async_poll, catching any finalized
	# that would result from the deletion of the last asynchronous data
	# structures.


# Note about this implementation
#
# A marginaly extended asyncore loop, with finalizations and defered, 
# asynchronous continuations as a piggy-back of the CPython GIL and the 
# simplest event scheduler possible, a heap queue (also a CPyton feature). 
#
# Expanding to more asynchronous event stack is not a "good thing" IMHO, 
# and certainly not to integrated peer networking with a GUI.
#
# It is implemented as a module (and not a class) because there is little
# use for two async loops in the same CPython VM. 
#
# Use two distinct processes instead ;-)
