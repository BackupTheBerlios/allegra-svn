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

from allegra.finalization import Finalization
from allegra.thread_loop import Thread_loop, Select_trigger


class Synchronizer (Select_trigger):

        def __init__ (self):
        	Select_trigger.__init__ (self)
		self.synchronized_thread_loops = []
		self.synchronized_instance_count = []
                self.synchronized_count = 0

	def __repr__ (self):
		return '<synchronizer/>'

	synchronizer_size = 4 # test for optimum on each OS

	def synchronizer_append (self):
		assert None == self.select_trigger.log (
			'<append count="%d"/>'  % len (
				self.synchronized_thread_loops
				)
			)
		new_thread = Thread_loop ()
		new_thread.thread_loop_queue.synchronizer_index = len (
			self.synchronized_thread_loops
			)
		self.synchronized_thread_loops.append (new_thread)
		self.synchronized_instance_count.append (0)
		new_thread.start ()
		
	def synchronize (self, instance):
		assert not hasattr (instance, 'synchronized')
		if self.synchronized_count == len (
                        self.synchronized_thread_loops
                        ) < self.synchronizer_size:
			self.synchronizer_append ()
		index = self.synchronized_instance_count.index (
			min (self.synchronized_instance_count)
			)
		instance.synchronized = self.synchronized_thread_loops[
			index
			].thread_loop_queue
		self.synchronized_instance_count[index] += 1
                self.synchronized_count += 1
		assert None == self.select_trigger.log (
			'<synchronized/>%r' % instance, ''
			)

	def desynchronize (self, instance):
		assert hasattr (instance, 'synchronized')
		i = instance.synchronized.synchronizer_index
		del instance.synchronized
		count = self.synchronized_instance_count[i]
                self.synchronized_count += -1
		self.synchronized_instance_count[i] += -1
		if count == 1:
			self.synchronized_thread_loops[i].thread_loop_stop ()
			del self.synchronized_thread_loops[i]
			del self.synchronized_instance_count[i]
		assert None == self.select_trigger.log (
			'<desynchronized/>%r' % instance, ''
			)


class Synchronized (Finalization):
        
        synchronizer = None
        
        def __init__ (self):
                if self.synchronizer == None:
                        Synchronized.synchronizer = Synchronizer ()
                self.synchronizer.synchronize (self)
                self.finalization = self.synchronizer.desynchronize
                

# Notes about this implementation
#
# The synchronizer is an resizable array of thread loop queues. Synchronized
# instances are attached to one of these queues. When a synchronized instance
# is finalized, that reference is released and the array is notified. When no
# more instance is attached to a thread loop queue, its thread exits. If the
# limit set on the array size is not reached, a new thread loop is created for
# each new synchronized instance. The default limit is set to 4.
#
# This interface is purely asynchronous: methods synchronized should be able
# to access the select_trigger to manipulate the Synchronizer, or more
# mundanely to push data to asynchat ...
#
# There is no easy way to prevent an instance to stall its thread loop queue
# and all the other instances methods synchronized to it. The only practical
# algorithm to detect a stalled method (and "fix" it), is to set a limit on
# the size of the synchronized queue and when that limit is reached to replace
# the stalled thread loop by a new one. However, this would leave the stalled
# thread to hang forever if the stalling method is running amok or blocking
# forever too. Setting a timeout on each synchronized method is impossible
# since there is no way to infer reliably a maximum execution time, certainly
# in such case of concurrent processes.
#
# Basicaly, there is no practicall and effective way to fix a thread broken by
# an infinite loop or a stalled-forever wait state. So, this implementation
# does not even attempt to correct the effects of such bugs on the other
# synchronized instance methods.
#
# Beware!
#
# Synchronized methods must be tested separately and that is trivial, because
# you may either test them asynchronously from within an async_loop host or,
# since they are synchronous, directly from the Python prompt.
#
# My advice is to use synchronized method in two cases: either you don't want
# to learn asynchronous programming, don't have time for it or perfectly know
# how to but need to access a blocking API that happens to be thread safe and
# releases the Python GIL (which means than threading it is faster). Like
#
# 	os.open (...).read ()
#
# or
#
#	bsddb.db.DB ().open (...)
#
