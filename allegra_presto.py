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

import sys, time

from allegra import loginfo, async_loop, http_server, presto_http

t = time.clock ()

if '-d' in sys.argv:
        sys.argv.remove ('-d')
        loginfo.Loginfo_stdio.log = \
                loginfo.Loginfo_stdio.loginfo_netlines
                
loginfo.log (
        'Allegra PRESTo!'
        ' - Copyright 2005 Laurent A.V. Szyster | Copyleft GPL 2.0',
        'info'
        )
        
root, ip, port, host = http_server.cli (sys.argv)

if ip.startswith ('127.'):
        server = http_server.HTTP_local ((ip, port))
elif ip.startswith ('192.168.') or ip.startswith ('10.') :
        server = http_server.HTTP_private ((ip, port))
else:
        server = http_server.HTTP_public ((ip, port))

server.http_hosts = dict ([
        (h, presto_http.PRESTo_http_root (p)) 
        for h, p in http_server.http_hosts (root, host, port)
        ])

server.async_catch = async_loop.async_catch
async_loop.async_catch = server.tcp_server_catch

del server

loginfo.log ('startup seconds="%f"' % (time.clock () - t), 'info')

async_loop.async_timeout = 1.0
async_loop.dispatch ()

sys.exit ()
