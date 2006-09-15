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

"http://laurentszyster.be/blog/tcp_server/"

import socket

from allegra import ip_peer, dns_client


def name_resolved (addr):
        "synchronously resolve a local address to itself"
        if addr[0].startswith ('127.'):
                return addr
        
        
def dns_PTR_resolve (addr, resolve):
        "resolve asynchronously an numeric IP address to a named one"
        def resolved (request):
                if request.dns_resources:
                        resolve ((request.dns_resources[0], addr[1]))
                else:
                        resolve (None)
        
        dns_client.lookup ((
                ip_peer.in_addr_arpa (addr[0]), 'PTR'
                ), resolved)

def dns_PTR_resolved (listen):
        "decorate a server abstraction with DNS address resolution"
        listen.server_resolved = name_resolved
        listen.server_resolve = dns_PTR_resolve
        return listen


def dns_double_lookup (addr, resolve):
        "resolve the name of a numeric IP address if it is reversed"
        def resolve_PTR (request):
                if request.dns_resources:
                        name = request.dns_resources[0]
                        def resolve_A (request):
                                if (
                                        request.dns_resources and 
                                        request.dns_resources[0] == addr[0]
                                        ):
                                        resolve ((name, addr[1]))
                                else:
                                        resolve (None)

                        dns_client.lookup ((name, 'A'), resolve_A)
                else:
                        resolve (None)
        
        dns_client.lookup ((
                ip_peer.in_addr_arpa (addr[0]), 'PTR'
                ), resolve_PTR)

def dns_PTR_reversed (listen):
        "decorate a server abstraction with double lookup resolution"
        listen.server_resolved = name_resolved
        listen.server_resolve = dns_double_lookup
        return listen