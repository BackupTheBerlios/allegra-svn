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

import collections, os, subprocess

from allegra import loginfo, finalization, thread_loop 


class Synchronizer (loginfo.Loginfo):

        def __init__ (self, size=2):
                self.synchronizer_size = size
		self.synchronized_thread_loops = []
		self.synchronized_instance_count = []
                self.synchronized_count = 0

	def __repr__ (self):
		return 'synchronizer pid="%x" count="%d"' % (
                        id (self), self.synchronized_count
                        )

	def synchronizer_append (self):
		assert None == self.log (
                        'append %d' % len (self.synchronized_thread_loops), 
                        'synchronizer'
                        )
		t = thread_loop.Thread_loop ()
		t.thread_loop_queue.synchronizer_index = len (
			self.synchronized_thread_loops
			)
		self.synchronized_thread_loops.append (t)
		self.synchronized_instance_count.append (0)
		t.start ()
		
	def synchronize (self, instance):
		assert not hasattr (instance, 'synchronized')
		if self.synchronized_count == len (
                        self.synchronized_thread_loops
                        ) < self.synchronizer_size:
			self.synchronizer_append ()
		index = self.synchronized_instance_count.index (
			min (self.synchronized_instance_count)
			)
                t = self.synchronized_thread_loops[index]
		instance.synchronized = t.thread_loop_queue
                instance.select_trigger = t.select_trigger 
		self.synchronized_instance_count[index] += 1
                self.synchronized_count += 1
		assert None == self.log ('%r' % instance, 'synchronized')

	def desynchronize (self, instance):
		assert hasattr (instance, 'synchronized')
		i = instance.synchronized.synchronizer_index
		count = self.synchronized_instance_count[i]
                self.synchronized_count += -1
		self.synchronized_instance_count[i] += -1
                instance.select_trigger = instance.synchronized = None
		if self.synchronized_count == 0:
                        assert None == self.log ('stop %d threads' % len (
                                self.synchronized_thread_loops
                                ), 'synchronizer')
                        for t in self.synchronized_thread_loops:
                                t.thread_loop_queue (None)
			self.synchronized_thread_loops = []
		assert None == self.log ('%r' % instance, 'desynchronized')


def synchronize (instance):
        if instance.synchronizer == None:
                instance.__class__.synchronizer = Synchronizer (
                        instance.synchronizer_size
                        )
        instance.synchronizer.synchronize (instance)


def desynchronize (instance):
        instance.synchronizer.desynchronize (instance)


def synchronized (instance):
        assert isinstance (instance, finalization.Finalization) 
        if instance.synchronizer == None:
                instance.__class__.synchronizer = Synchronizer (
                        instance.synchronizer_size
                        )
        instance.synchronizer.synchronize (instance)
        instance.finalization = instance.synchronizer.desynchronize


# Synchronized methods for file I/O, typical synchronized functions that
# call thread-safe and GIL-releasing builtin or binded fast C libraries.

def sync_open (self, filename, mode):
        try:
                self.sync_file = open (filename, mode)
        except:
                self.select_trigger ((self.async_close, ('eo')))
        if mode[0] == 'r':
                self.sync_read ()
        
def sync_write (self, data):
        try:
                self.sync_file.write (data)
        except:
                self.select_trigger ((self.async_close, ('ew')))
        
def sync_read (self):
        try:
                data = self.sync_file.read (self.sync_buffer)
        except:
                self.select_trigger ((self.async_close, ('er')))
        else:
                if data:
                        self.select_trigger ((self.async_read, (data, )))
                else:
                        self.sync_close ('r')
        
def sync_close (self, mode):
        try:
                self.sync_file.close ()
        except:
                self.select_trigger ((self.async_close, ('ec', )))
        else:
                self.select_trigger ((self.async_close, (mode, )))
        self.sync_file = None
        

class Synchronized_open (object):
        
        # either buffers a synchronous file opened read-only and provide
        # a stallable producer interface, or write synchronously to a
        # file the data provided by the instance collector interface.
        #
        # practically, this is a synchronized file reactor.
        
        synchronizer = None
        synchronizer_size = 4
        
        collector_is_simple = True
        
        async_buffers = ()
        async_closed = False

        def __init__ (self, filename, mode='r', buffer=4096):
                self.sync_buffer = buffer
                if mode[0] == 'r':
                        self.async_buffers = collections.deque([])
                synchronize (self)
                self.synchronized ((self.sync_open, (filename, mode)))
                        
        def __repr__ (self):
                return 'synchronized-open id="%x"' % id (self)
                        
        # a reactor interface
                
        def collect_incoming_data (self, data):
                self.synchronized ((self.sync_write, (data,)))
                
        def found_terminator (self):
                self.synchronized ((self.sync_close, ()))
                
        def more (self):
                try:
                        return self.async_buffers.popleft ()
                        
                except:
                        return ''
                        
        def producer_stalled (self):
                return not (
                        self.async_closed or len (self.async_buffers) > 0
                        )
                        
        # >>> Synchronized methods
        
        sync_open = sync_open
        sync_write = sync_write
        sync_read = sync_read
        sync_close = sync_close

        # ... asynchronous continuations
                
        def async_read (self, data):
                self.async_buffers.append (data)
                self.synchronized ((self.sync_read, ()))
                
        def async_close (self, mode):
                self.async_closed = True
                desynchronize (self)
                                
                                
# Synchronized Subprocess methods
                                
def sync_popen (self, args, kwargs):
        # try to open a subprocess and either write input and/or
        # poll output. Return on exception.
        try:
                self.subprocess = subprocess.Popen (*args, **kwargs)
        except:
                self.select_trigger ((self.async_return, (None, )))
                return
        
        if self.subprocess.stdin == None:
                self.sync_poll ()
        else:
                self.sync_stdin ()

def sync_stdin (self, data):
        # try to write and poll, or return
        try:
                self.subprocess.stdin.write (data)
        except:
                self.select_trigger ((
                        self.async_return, ('subprocess.stdin.write error', )
                        ))
                return
        
        self.sync_poll ()
        
def sync_poll (self):
        # try to poll, return when done or on exception ...
        try:
                code = self.subprocess.poll ()
        except:
                self.select_trigger ((
                        self.async_return, ('subprocess.poll error', )
                        ))
                return
        
        if code != None:
                self.select_trigger ((self.async_return, (code, )))
                return
        
        # ... continue either by reading stdout and stderr if any
        if self.subprocess.stdout != None:
                try:
                        stdout = self.subprocess.stdout.read (
                                self.sync_buffer
                                )
                except:
                        self.select_trigger ((
                                self.async_return, (
                                        'subprocess.stdout.read error', 
                                        )
                                ))
                        return
                
        if self.subprocess.stderr != None:
                try:
                        stderr = self.subprocess.stderr.read (
                                self.sync_buffer
                                )
                except:
                        self.select_trigger ((
                                self.async_return, (
                                        'subprocess.stderr.read error', 
                                        )
                                ))
                        return
                
        self.select_trigger ((self.async_read, (stdout, stderr)))
                                
def sync_wait (self):
        self.select_trigger ((self.async_return, (self.subproces.wait (), )))


class Synchronized_popen (finalization.Finalization):
        
        # another reactor interface for synchronous system call, here
        # a popened process. Data is collected to STDIN, STDOUT is 
        # buffered to produce output and STDERR is collected.
        
        synchronizer = None
        synchronizer_size = 4

        collector_is_simple = True
        
        sync_buffer = 4096
        async_code = None
        
        def __init__ (self, *args, **kwargs):
                self.async_stdout = collections.deque([])
                synchronize (self)
                self.synchronized ((self.sync_popen, (args, kwargs)))
                
        def collect_incoming_data (self, data):
                self.synchronized ((self.sync_stdin, (data,)))
                
        def found_terminator (self):
                self.synchronized ((self.sync_poll, ()))
                return True
        
        def more (self):
                try:
                        return self.async_stdout.popleft ()
                        
                except:
                        return ''
        
        def producer_stalled (self):
                return not (
                        self.async_code == None or 
                        len (self.async_stdout) > 0
                        )

        sync_popen = sync_popen
        sync_stdin = sync_stdin
        sync_poll = sync_poll
        sync_wait = sync_wait
        
        def async_read (self, stdout, stderr):
                self.async_stdout.append (stdout)
                self.async_stderr.append (stderr)
                self.synchronized ((self.sync_poll, ()))
                
        def async_return (self, code):
                self.async_code = code
                assert None == loginfo.log ('%r' % code, 'debug')
        
# TODO: add synchronized file and process reactors
#
# something like:
#
#        fs ('~').read|write ('/name')
#
#        ps ('command').stdout|stderr|stdin ()
#
# Notes about this implementation
#
# The purpose is to but deliver non-blocking access to three synchronous
# system API: stat, open and popen.
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
# Basicaly, there is no practical and effective way to fix a thread broken by
# an infinite loop or a stalled-forever wait state. So, this implementation
# does not even attempt to correct the effects of such bugs on the other
# synchronized instance methods.
#
# Beware!
#
# Synchronized methods must be tested separately. Yet it is trivial, because
# you may either test them asynchronously from within an async_loop host or,
# since they are synchronous, directly from the Python prompt.
#
# My advice is to use synchronized method in two cases. Either you don't want
# to learn asynchronous programming (don't have time for that). Or you know
# how, but need to access a blocking API that happens to be thread safe and
# releases the Python GIL.
#
# For instance:
#
# 	os.open (...).read ()
#
# or
#
#	bsddb.db.DB ().open (...)
#
# may be blocking and should be synchronized.