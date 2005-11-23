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

import time, collections

from allegra import async_loop


class Timeouts:
	
	# for many applications you may as well check for any timeouts due
	# every seconds.
	
	def __init__ (self, timeout, period, precision=None):
		self.timeouts_timeout = timeout
		self.timeouts_period = max (period, async_loop.async_timeout)
		self.timeouts_precision = precision or async_loop.async_timeout
		self.timeouts_deque = collections.deque ()
		async_loop.async_schedule (
			time.time () + self.timeouts_precision,
			lambda w, t=self:t.timeouts_defer (w)
			) # defer ...
		
        def timeouts_push (self, reference):
		self.timeouts_deque.append ((time.time (), reference))
		return reference
	
	def timeouts_defer (self, now):
		then = now - self.timeouts_precision - self.timeouts_period 
		while len (self.timeouts_deque) > 0:
			when, reference = self.timeouts_deque[0]
			if  when < then:
				self.timeouts_deque.popleft ()
				self.timeouts_timeout (reference)
			else:
				break
				
		return (
			now + self.timeouts_precision,
			lambda w, t=self: t.timeouts_defer (w)
			) # ... continue to defer ...

	# to stop the Timeouts, simply do:
	#
	#	self.timeouts_defer = self.timeouts_stop
	#
	def timeouts_stop (self, when):
		del self.timeouts_defer, self.timeouts_timeout
		#
		# ... break the circular reference on last defer.
	
	
# Note about this implementation	
#
# Having now peaked at both twisted, ACE and the libevent interfaces, I can
# proudly say that the async_loop.async_schedule and the timeouts.Timeouts
# interfaces are better.
#
# Allegra offers three kind of time events: single events defered at a fixed 
# interval of time (ie the classic timeout) and single or recurent events 
# scheduled at varying.
#
#
# Schedule
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
# Time out
#
# In order to scale up and handle very large number of timeouts scheduled
# asynchronously at fixed intervals, this module provides a simple deque 
# interface that for a fifo of timeout events to poll from.
#
# Polling a timeouts queue should be scheduled recurrently more or less
# precise intervals depending on the volume expected and the time it takes
# to handle each timeout. Your mileage may vary, but this design will scale
# up in the case of long intervals, when for each time poll only a few first 
# events at the left of the deque have timed-out.
#
# The timouts interface is applied by pns_udp to manage the 3 second timeout
# set on each statement relayed or routed by a PNS/UDP circle. There might
# be other applications, RTP protocols for instance.