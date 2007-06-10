# Copyright (C) 2006-2007 Laurent A.V. Szyster
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

import sys
from allegra import async_loop, finalization, anoption

def main (
    database=':memory:', host='127.0.0.2', port=3999,
    precision=1.0, inactive=3.0, local=512, private=1, public=1,
    log_buffer_size=4096, anetlog_host='', anetlog_port=3998
    ):
    import time
    started = time.time ()
    from allegra import netstring, loginfo, tcp_server, ansqlite
    if anetlog_host:
            from allegra import anetlog
            anetlog.stdoe ((anetlog_host, anetlog_port))
    loginfo.log (
        'ansqlite - Copyright 2007 Laurent Szyster | Copyleft GPL 2.0', 'info'
        )
    conn, Dispatcher = ansqlite.open (database)
    ansql = Dispatcher.ansql 
    loads = ansqlite.loads
    for data in netstring.netpipe ((
        lambda r=sys.stdin.read: r (log_buffer_size)
        )):
        ansql (*loads(data)).close ()
    del ansql, loads
    listen = tcp_server.decorate (tcp_server.Listen (
        Dispatcher, (host, port), precision, max=5
        ), inactive, local, private, public)
    async_loop.catch (listen.server_shutdown)
    def finalize (listen):
        anetlog.disconnect ()
        conn.close ()
        
    listen.finalization = finalize
    del listen
    loginfo.log ('loaded in %f seconds' % (time.time () - started), 'info')
    
anoption.cli (main, sys.argv[1:])
async_loop.dispatch ()
assert None == finalization.collect ()