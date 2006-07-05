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

"http://laurentszyster.be/blog/timeouts/"

import time, collections

from allegra import async_loop


class Timeouts (object):
	
	def __init__ (self, timeout, period, precision=None):
		self.timeouts_timeout = timeout
		self.timeouts_period = max (period, async_loop.precision)
		self.timeouts_precision = precision or async_loop.precision
		self.timeouts_deque = collections.deque ()
		async_loop.schedule (
			time.time () + self.timeouts_precision,
			self.timeouts_schedule
			)
		
        def timeouts_push (self, reference):
		self.timeouts_deque.append ((time.time (), reference))
		return reference
	
	def timeouts_schedule (self, now):
		then = now - self.timeouts_precision - self.timeouts_period 
		while self.timeouts_deque:
			when, reference = self.timeouts_deque[0]
			if  when < then:
				self.timeouts_deque.popleft ()
				self.timeouts_timeout (reference)
			else:
				break
				
		return self.timeouts_continue (now)

	def timeouts_continue (self, now):
		return (
			now + self.timeouts_precision, 
			self.timeouts_schedule
			)	

	# to stop the Timeouts, simply do:
	#
	#	self.timeouts_continue = self.timeouts_stop
	#
	def timeouts_stop (self, when):
		del self.timeouts_continue, self.timeouts_timeout
		#
		# ... break the circular reference on last schedule.
	

# The first, simplest and probably most interesting application of Timeouts

def cached (cache, period, precision):
        def timeout (reference):
                try:
                        del cache[reference]
                except KeyError:
                        pass
        
        t = Timeouts (timeout, period, precision)
        def push (key, value):
                cache[key] = value
                t.timeouts_push (key)
                
        def stop ():
                t.timeouts_continue = t.timeouts_stop
                
        return push, stop

# push, stop = timeouts.cached ({}, 60, 6)
# ...
# push (key, value)
# ...
# stop ()
        
# Note about this implementation	
#
# Time out
#
# In order to scale up and handle very large number of timeouts scheduled
# asynchronously at fixed intervals, this module provides a simple deque 
# interface that for a fifo of timeout events to poll from.
#
# Polling a timeouts queue should be scheduled recurrently at more or less
# precise intervals depending on the volume expected and the time it takes
# to handle each timeout. Your mileage may vary, but this design will scale
# up in the case of long intervals, when for each time poll only a few first 
# events at the left of the deque have timed-out.
#
# The timouts interface is applied by pns_udp to manage the 3 second timeout
# set on each statement relayed or routed by a PNS/UDP circle. There might
# be other applications, RTP protocols for instance.