# Copyright (C) 2006 Laurent A.V. Szyster
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

"http://laurentszyster.be/blog/ansqlite/"

import sys, time

from allegra import (
        netstring, loginfo, async_loop, finalization, 
        ip_peer, tcp_client, ansqlite
        )

loads = ansqlite.loads
dumps = ansqlite.dumps
try:
        statements = netstring.netpipe (
                lambda r=sys.stdin.read: r (4096)
                )
        addr = ip_peer.addr (sys.argv[1], 3999)
        clients = int (sys.argv[2])
except:
        loginfo.traceback ()
        sys.exit (1)

class Dispatcher (ansqlite.Client):

        statements_count = 0

        def callback (self, resultset):
                assert None == loginfo.log ('%r' % resultset)
                try:
                        stmt, param = loads (statements.next ())
                except StopIteration:
                        self.handle_close ()
                except:
                        self.loginfo_traceback ()
                else:
                        Dispatcher.statements_count += 1
                        self (self.callback, stmt, param)
        
try:
        for ansql in (Dispatcher () for i in xrange (clients)):
                if tcp_client.connect (ansql, addr):
                        stmt, param = loads (statements.next ())
                        Dispatcher.stmt_count += 1
                        if Dispatcher.stmt_count < Dispatcher.stmt_limit:
                                sql (sql.test_callback, stmt, param)
except:
        loginfo.traceback ()
        sys.exit (2)
        
started = time.time ()
async_loop.dispatch ()
finalization.collect ()
loginfo.log ('%d statements in %f seconds' % (
        Dispatcher.stmt_count, time.time () - started
        ), 'info')
sys.exit (0)

# Here's the idea: open with N client connections playing a sequence
# of statements over, but starting at random, stop when the given count 
# of requests made is reached, synchronize the next request with the last
# response. This is a next-best simulation of N user agent banging the
# database access controller implemented by the SQL peer application.
#
# The question is how many SQL transactions like X, Y and Z can a single
# asynchronous database handle per second, preferably loaded with real data.
#        
# That's how you develop a test driven application.
#
# A thousand unit test did not save Twisted from beeing Broken, they
# are "creativity killers" all bored and mediocre programmers endulge
# in order to boost their code metrics and offer their pointy haired
# boss a green image of reliability. The code pass many tests made of
# more code.
#
# Mind you, there is only one valid test, the application tests case. 
#
# Tested applications are in demand, not tested code.
#
# So, here's the test cases: feed and time the simplest benchmark data sets
# available, ones that test load for row SELECT, UPDATE, INSERT and DELETE.
#
# Select a limited count of rows, update, insert and delete one or a few 
# many rows. The purpose of the test is to compare how fast two asynchronous
# peers can get as none suffers from contention and latency, handling 
# gracefully high level of concurrency for both.
#
# My bet is that it can easely outperform any LAMP combo at high levels
# of concurrency. Because the waite state induced by latency and contention
# in the database does not impact on the CPU load of the transaction
# controller (ie: a web application).
#
# Here not much is lost from C in terms of speed in SQL interpretation and 
# result set serialization and deserialization. This is very quickly done by 
# the cPickle and SQLite C modules. Allegra adds as little Python as possible 
# to glue it all safely together for network peers.
#
# If you need to scale up a statefull web application of an SQL database,
# this may well be a piece for a worthy Python contender to J2EE.