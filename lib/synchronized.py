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

"http://laurentszyster.be/blog/synchronized/"

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
                        sync_close (self, 'r')
        
def sync_close (self, mode):
        try:
                self.sync_file.close ()
        except:
                self.select_trigger ((self.async_close, ('ec', )))
        else:
                self.select_trigger ((self.async_close, (mode, )))
        self.sync_file = None
        

class File_producer (object):

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
                self.synchronized ((sync_open, (self, filename, mode)))

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
                        
        def async_open (self, mode):
                self.synchronized ((sync_read, (self, )))
        
        def async_read (self, data):
                self.async_buffers.append (data)
                self.synchronized ((sync_read, (self, )))
                
        def async_close (self, mode):
                self.async_closed = True
                thread_loop.desynchronize (self)
                                

class File_collector (object):

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
                self.synchronized ((sync_open, (self, filename, mode)))

        def __repr__ (self):
                return 'synchronized-file-collector id="%x"' % id (self)
                
        def collect_incoming_data (self, data):
                self.synchronized ((sync_write, (self, data,)))
                
        def found_terminator (self):
                self.synchronized ((sync_close, (self, 'w', )))

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
                sync_poll (self)
        #else:
        #        sync_stdin (self)

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
        self.synchronized ((sync_poll, (self, )))
                
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


class Popen_reactor (object):
        
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
                self.synchronized ((sync_popen, (self, args, kwargs)))
                
        def collect_incoming_data (self, data):
                self.synchronized ((sync_stdin, (self, data,)))
                
        def found_terminator (self):
                self.synchronized ((sync_poll, (self, )))
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

        def async_read (self, stdout):
                self.async_stdout.append (stdout)
                self.synchronized ((sync_poll, (self, )))
                
        def async_return (self, code):
                self.async_code = code
                thread_loop.desynchronize (self)
                assert None == loginfo.log ('%r' % code, 'debug')


class Pipe_reactor (Popen_reactor, finalization.Finalization):

        synchronizer_size = 16
        
        def __init__ (self, args):
                Popen.__init__ (
                        self, args, 0, None, 
                        subprocess.PIPE, subprocess.PIPE, subprocess.STDOUT
                        )

