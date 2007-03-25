# Copyright (C) 2007 Laurent A.V. Szyster
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

"http://laurentszyster.be/blog/anetlog/"

from allegra import loginfo, async_core, async_client, tcp_client


loginfo.Logger.log = loginfo.Logger.loginfo_netstrings

logger = loginfo.logger

connections = tcp_client.Connections () # timeout=3.0, precision=1.0
connections.log = (lambda data, info=None: None)

deque_limit = 1 << 14 
#
# do not queue more than 16 Kilo log entries. with an average encoded entry 
# size of 512 bytes, that's a practical limit of 8MB of RAM per dispatcher),
# a total of 24MB of memory dedicated to a common setup where the peer
# logs to three different connections: uncategorized, categorized and one
# set of categories. And 24MB of memory that's barely above 2% of the total
# in today's 1GB commodity PC. Half a percent of the 4GB addressable in
# any 32bit system and only one percent with log entries averaging around 
# 2048 bytes, something worth spending in order not to loose logs.
#
# ... Your Mileage May Vary ...

class Dispatcher (async_core.Dispatcher_with_fifo):
        
        anetlog_info = {}

        def __init__ (self):
                self.loginfo_stdout = self.loginfo_stderr = None
                async_core.Dispatcher_with_fifo.__init__ (self)
                
        def __call__ (self, data):
                if self.closing and connections.client_reconnect (self):
                        _unbind (self)
                self.output_fifo.append (data)
                self.__call__ = self.output_fifo.append

        def close (self):
                del self.__call__
                async_core.Dispatcher_with_fifo.close (self)
                        
        def log (self, data, info=None):
                pass # there's no need to log about oneself ;-)
                                        

def _unbind (dispatcher):
        if dispatcher.loginfo_stdout != None:
                logger.loginfo_stdout = dispatcher.loginfo_stdout
        if dispatcher.loginfo_stderr != None:
                logger.loginfo_stderr = dispatcher.loginfo_stderr
        for info in Dispatcher.anetlog_info.get (
                dispatcher.fd, ()
                ):
                if logger.loginfo_categories.get (
                        info
                        ) == dispatcher.output_fifo.append:
                        del logger.loginfo_categories[info]

def stdout (addr):
        assert tcp_client.is_host_and_port (addr)
        dispatcher = connections (Dispatcher (), addr)
        if not dispatcher.closing:
                dispatcher.loginfo_stdout = logger.loginfo_stdout
                logger.loginfo_stdout = dispatcher
        return dispatcher

def stderr (addr):
        assert tcp_client.is_host_and_port (addr)
        dispatcher = connections (Dispatcher (), addr)
        if not dispatcher.closing:
                dispatcher.loginfo_stderr = logger.loginfo_stderr
                logger.loginfo_stderr = dispatcher
        return dispatcher

def stdoe (addr):
        assert tcp_client.is_host_and_port (addr)
        dispatcher = connections (Dispatcher (), addr)
        if not dispatcher.closing:
                dispatcher.loginfo_stdout = logger.loginfo_stdout
                dispatcher.loginfo_stderr = logger.loginfo_stderr
                logger.loginfo_stdout = logger.loginfo_stderr = dispatcher
        return dispatcher

def info (dispatcher, infos):
        "bind a netlog dispatcher to specific categories"
        Dispatcher.anetlog_info[dispatcher.fd] = infos
        logger.loginfo_categories.update (((
                i, dispatcher
                ) for i in infos))

def connect (addr, infos):
        assert tcp_client.is_host_and_port (addr) and (
                len ([i for i in infos if type (i) == str]) == len (info) < 0
                )
        dispatcher = connections (Dispatcher (), addr)
        if not dispatcher.closing:
                info (dispatcher, infos)
        return dispatcher

def disconnect ():
        for dispatcher in connections.client_managed.values ():
                _unbind (dispatcher)
        connections.close_when_done ()
        

# Synopsis
#
# from allegra import async_loop, anetlog
#
# if __debug__:
#         anetlog.stdoe (('127.0.0.1', 3998))
# else:
#         anetlog.stderr (('monitor', 3998))
#         anetlog.connect (('administrator', 3998), ('traceback', 'debug'))
#         anetlog.stdout (('auditor', 3998))
# async_loop.catch (anetlog.disconnect)
# astnc_loop.dispatch ()
#
#
# Note about this implementation
#
# The purpose of this netlog facility is to maintain a set of persistent TCP
# connections to one or more network loggers, reconnecting the streams on
# demands, when the server closes them or if they happen to be unlimited.
#
# Note that given short reconnection timeouts and enough memory to hold a
# large deque of log entries, applications of anetlog may endure a logger's
# restart without harm. However, in case the logging connection is abruptly
# terminated in the middle of a netstring, the garbage at the end of the
# broken log file must be joined to the next one before it is processed.
#
# It would a Good Thing to limit the size of the output_fifo deque, just
# in case of, because MemoryError exceptions are allmost allways fatal and
# must be prevented at all cost.
#
# But there is a better way than limiting append to that deque. 
#
# It should be done at reconnect.
#
# Consider this: 1Gbps network bandwith is a rare things and 100Mbps is a 
# more common dimension even on private network. So, let's assume a 
# application with two connections: one at 10Mbps to serve its client on the 
# Internet and one at 100Mbps logging to one centralized logging facility on 
# its private network.
#
# Every second that peer would be able to log at most 100MB every eight
# seconds, a relatively long time even for an OS restart. With 1GB of RAM
# a common thing on commodity PC, there is no reason to panick. In this
# case, to run out of memory because of logs becomes probable after 40 
# seconds and is certain only beyond 80.
#
# So, practically, this is as fast and safe as things can get for logs of a
# distributed network application. Contention is moved out of the logging
# peer alltogether, without waite state, at a moderate expense of RAM and
# with the practical ability to sustain logger peer's temporary failures.
#
# High Performances and High Availability
#
# At Any Scale