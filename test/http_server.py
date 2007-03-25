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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

def main (
    ip='127.0.0.2', port=80,
    precision=1.0, inactive=3.0, local=256, private=16, public=2
    ):
    from allegra import async_server, tcp_server, http_server
    listen = tcp_server.decorate(async_server.Listen (
        http_server.Dispatcher, (ip, port), precision, 
        tcp_server.LISTEN_MAX
        ), inactive, local, private, public)
    def http_404_not_found (reactor):
        reactor.http_response (404) # Not Found
                
    listen.http_continue = http_404_not_found
    async_loop.catch (listen.server_shutdown)

import sys
from allegra import async_loop, finalization, anoption
anoption.cli (main, sys.argv[1:])
async_loop.dispatch ()
assert None == finalization.collect ()
sys.exit (0)