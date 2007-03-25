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

import os, socket

from allegra import async_loop, async_server, ip_peer, dns_client


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


if os.name == 'nt':
        LISTEN_MAX = 5
else:
        LISTEN_MAX = 1024


def decorate (
        listen, inactive, local, private, public, resolved=dns_PTR_resolved
        ):
        ip = listen.addr[0]
        concurrency_50 = async_loop.concurrency / 2
        if ip.startswith ('127.'):
                async_server.accept_named (listen, min (
                        max (local, 1), concurrency_50
                        ))
        else:
                if ip.startswith ('192.168.') or ip.startswith ('10.'):
                        async_server.accept_named (listen, min (
                                max (private, 1), concurrency_50
                                ))
                else:
                        async_server.accept_named (listen, min (
                                max (public, 2), concurrency_50
                                ))
                async_server.inactive (listen, min (inactive, 3.0))
                resolved (listen)
        return listen

# The ultimate convenience: decorate TCP/IP servers relevantly according
# to its runtime environment (development/production) and the degree of
# privacy of its network address: personal , private or public.
#
# Wether it's an HTTP or an SQL server, enforcing resolution and connection
# limits is an aspect of the same application: TCP/IP access control. This
# is one obvious way to do it right, conveniently provided as an extensible
# function (you can replace the default resolution decorator). 

        