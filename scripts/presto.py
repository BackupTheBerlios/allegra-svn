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

def main (
    root='.',
    precision=1.0, inactive=3.0, local=512, private=1, public=1,
    anetlog_host='', anetlog_port=3998,
    ac_in=16384, ac_out=16384 
    ):
    import time
    started = time.time ()
    from allegra import loginfo, ip_peer, tcp_server, http_server, presto
    http_server.Dispatcher.ac_in_buffer_size = ac_in
    http_server.Dispatcher.ac_out_buffer_size = ac_out
    if anetlog_host:
            from allegra import anetlog
            anetlog.stdoe ((anetlog_host, anetlog_port))
            def finalize (joined):
                anetlog.disconnect ()
                loginfo.log ('final', 'info')

    else:
        def finalize (joined):
            loginfo.log ('final', 'info')
            
    loginfo.log (
        'Allegra PRESTo'
        ' - Coyright 2005-2007 Laurent A.V. Szyster'
        ' | Copyleft GPL 2.0',
        'info'
        )
    import glob, os, stat
    joined = finalization.Finalization ()
    for listen in [
        tcp_server.decorate (presto.Listen (
            path, addr, precision
            ), inactive, local, private, public)
        for path, addr in [
            (
                    p.replace ('\\', '/'), 
                    ip_peer.addr (os.path.basename (p), 80)
                    )
            for p in glob.glob ('%s/*' % root)
            if stat.S_ISDIR (os.stat (p)[0])
            ]
        ]:
        for filename in listen.presto_dir ():
                listen.presto_load (filename)
        async_loop.catch (listen.server_shutdown)
        listen.finalization = joined
    joined.finalization = finalize
    loginfo.log ('loaded in %f seconds' % (time.time () - started), 'info')

import sys
from allegra import async_loop, finalization, anoption
anoption.cli (main, sys.argv[1:])
async_loop.dispatch ()
assert None == finalization.collect ()
sys.exit (0)