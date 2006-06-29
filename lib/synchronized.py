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

import collections, subprocess

from allegra import loginfo, finalization, thread_loop 


# File producer and collector

def sync_open (self, filename, mode):
        try:
                self.sync_file = open (filename, mode)
        except:
                self.select_trigger ((self.async_close, ('eo', )))
        else:
                self.select_trigger ((self.async_open, (mode, )))
        
def sync_write (self, data):
        try:
                self.sync_file.write (data)
        except:
                self.select_trigger ((self.async_close, ('ew', )))
        
def sync_read (self):
        try:
                data = self.sync_file.read (self.sync_buffer)
        except:
                self.select_trigger ((self.async_close, ('er', )))
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
        

class File_producer (finalization.Finalization):

        synchronizer = None
        synchronizer_size = 4
        
        async_buffers = ()
        async_closed = False

        def __init__ (self, filename, mode='rb', buffer=4096):
                assert (
                        type (filename) == str and
                        mode.startswith ('r') and 
                        (0 < len (mode) < 3) and
                        buffer > 0
                        )
                self.sync_buffer = buffer
                self.async_buffers = collections.deque([])
                thread_loop.synchronize (self)
                self.synchronized ((self.sync_open, (filename, mode)))

        def __repr__ (self):
                return 'synchronized-file-producer id="%x"' % id (self)
                        
        def more (self):
                try:
                        return self.async_buffers.popleft ()
                        
                except:
                        return ''
                        
        def producer_stalled (self):
                return not (
                        self.async_closed or len (self.async_buffers) > 0
                        )
                        
        sync_open = sync_open
        sync_read = sync_read
        sync_close = sync_close
        
        def async_open (self, mode):
                self.synchronized ((self.sync_read, ()))
        
        def async_read (self, data):
                self.async_buffers.append (data)
                self.synchronized ((self.sync_read, ()))
                
        def async_close (self, mode):
                self.async_closed = True
                thread_loop.desynchronize (self)
                                

class File_collector (finalization.Finalization):

        synchronizer = None
        synchronizer_size = 4
        
        collector_is_simple = True
        
        async_closed = False

        def __init__ (self, filename, mode='wb'):
                assert (
                        type (filename) == str and
                        not mode.startswith ('r') and 
                        (0 < len (mode) < 3)
                        )
                thread_loop.synchronize (self)
                self.synchronized ((self.sync_open, (filename, mode)))

        def __repr__ (self):
                return 'synchronized-open id="%x"' % id (self)
                
        def collect_incoming_data (self, data):
                self.synchronized ((self.sync_write, (data,)))
                
        def found_terminator (self):
                self.synchronized ((self.sync_close, ('w', )))

        sync_open = sync_open
        sync_write = sync_write
        sync_close = sync_close
        
        def async_open (self, mode): pass
        
        def async_close (self, mode):
                self.async_closed = True
                thread_loop.desynchronize (self)


# Subprocess reactor               
                                
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
        
        # ... maybe reading stdout ...
        if self.subprocess.stdout != None:
                try:
                        stdout = self.subprocess.stdout.read (
                                self.sync_buffer
                                )
                except:
                        # ... terminate and return on exception ...
                        self.select_trigger ((
                                self.async_return, (
                                        'subprocess.stdout.read error', 
                                        )
                                ))
                else:
                        # ... to buffer asynchronously ...
                        self.select_trigger ((self.async_read, (stdout, )))
                return
        
        # ... or poll more >>>
        self.synchronized ((self.sync_poll, ()))
                
def sync_wait (self):
        try:
                stderr = self.subprocess.stderr.read ()
        except:
                self.select_trigger ((
                        self.async_return, (
                                'subprocess.stderr.read error', 
                                )
                        ))
        else:
                code = self.subproces.wait ()
                self.select_trigger ((self.async_return, (code, )))


class Synchronized_popen (object):
        
        # Another reactor interface for synchronous system call, here
        # a popened process. Data is collected asynchronously to STDIN, 
        # STDOUT is buffered to produce asynchronous output and STDERR 
        # is collected in a cStringIO buffer ... synchronously ;-)

        synchronizer = None
        synchronizer_size = 4

        collector_is_simple = True
        
        sync_buffer = 4096
        async_code = None
        
        def __init__ (self, *args, **kwargs):
                self.async_stdout = collections.deque([])
                thread_loop.synchronize (self)
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
        
        def async_read (self, stdout):
                self.async_stdout.append (stdout)
                self.synchronized ((self.sync_poll, ()))
                
        def async_return (self, code):
                self.async_code = code
                thread_loop.desynchronize (self)
                assert None == loginfo.log ('%r' % code, 'debug')
        
        # The rational is that you want to produce STDOUT not STDERR.
        #
        # Errors are "bagged" in one big buffer or any other file type
        # specified as SYNC_STDERR that is supported by the subprocess
        # standard module of Python 2.4.
        #
        # This class is a very practical way to pipe UNIX processes
        # with Command Line Interface through asynchronously network
        # I/O, with the least blocking possible given a maximum number 
        # of threads.
        #
        # It's methods and design is reused by PRESTo components to
        # provide a CGI-like interface for Allegra's web framework. It
        # may be applied to all those CPU intensive processes for which
        # a reliable and optimized pipes allready exists.
        #
        # Further processing of the reactor's output or input can be
        # implemented by chaining the ad-hoc type of collector and/or 
        # producer instances.


class Pipe_reactor (Synchronized_popen, finalization.Finalization):

        synchronizer_size = 16
        
        def __init__ (self, args):
                Synchronized_popen.__init__ (
                        self, args, 0, None, 
                        subprocess.PIPE, subprocess.PIPE, None
                        )

        #
        # Uses up to 16 threads to synchronize subprocess with the
        # asynchronous collector and producer interfaces, piping
        # in collected data, producing the subprocess STDOUT and
        # not even looking at STDERR.


# Synchronized file and process reactors
#
# This modules comes with two usefull asynchronous reactors that can collect
# and/or produce data to/from a synchronous file or process.