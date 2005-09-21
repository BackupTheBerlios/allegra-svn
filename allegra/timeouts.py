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

from time import time

from allegra import async_loop
from allegra.fifo import FIFO_big


class Timeouts:
	
	# for many applications you may as well check for any timeouts due
	# every seconds.
	
	def __init__ (self, timeout, period, precision=None):
		self.timeouts_timeout = timeout
		self.timeouts_period = max (period, async_loop.async_timeout)
		self.timeouts_precision = precision or async_loop.async_timeout
		self.timeouts_fifo = FIFO_big ()
		async_loop.async_defer (
			time () + self.timeouts_precision,
			lambda w, t=self:t.timeouts_defer (w)
			) # defer ...
		
        def timeouts_push (self, reference):
		self.timeouts_fifo.push ((time (), reference))
		return reference
	
	def timeouts_defer (self, now):
		then = now - self.timeouts_precision - self.timeouts_period 
		while not self.timeouts_fifo.is_empty ():
			when, reference = self.timeouts_fifo.first ()
			if  when < then:
				self.timeouts_fifo.pop ()
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
		
