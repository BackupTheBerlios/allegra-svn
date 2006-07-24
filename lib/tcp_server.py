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

import socket

from allegra import async_client, ip_peer, dns_client


def name_resolved (addr):
        if addr[0].startswith ('127.'):
                return addr
        

def dns_PTR_resolve (addr, resolve):
        def resolved (request):
                if request.dns_resources:
                        resolve ((request.dns_resources[0], addr[1]))
                else:
                        resolve (None)
        
        dns_client.lookup ((
                ip_peer.in_addr_arpa (addr[0]), 'PTR'
                ), resolved)


def dns_PTR_resolved (listen):
        listen.server_resolved = name_resolved
        listen.server_resolve = dns_PTR_resolve
        return listen

