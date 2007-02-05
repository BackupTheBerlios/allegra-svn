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

"http://laurentszyster.be/blog/tcp_client/"

import socket

from allegra import async_client, ip_peer, dns_client


def is_host_and_port (addr):
        "test that addr is a tuple of one string and an integer"
        return (
                type (addr) == tuple and 
                len (addr) == 2 and
                type (addr[0]) == str and
                type (addr[1]) == int
                )

def ip_resolved (addr):
        "synchronously resolve a numeric IP name to itself"
        if ip_peer.is_ip (addr[0]):
                return addr

def dns_A_resolve (addr, resolve):
        "resolve asynchronously a named address to a numeric one"
        def resolved (request):
                if request.dns_resources:
                        resolve ((request.dns_resources[0], addr[1]))
                else:
                        resolve (None)
        dns_client.lookup ((addr[0], 'A'), resolved)


def connect (
        dispatcher, name, timeout=3.0, 
        resolved=ip_resolved, resolve=dns_A_resolve
        ):
        "resolve and maybe connect a dispatcher, close on error"
        assert not dispatcher.connected
        addr = resolved (name)
        if addr != None:
                return async_client.connect (
                        dispatcher, addr, timeout, socket.AF_INET
                        )

        if resolve == None:
                dispatcher.handle_close ()
                return False
        
        def connect_or_close (addr):
                if addr == None:
                        dispatcher.handle_close ()
                else:
                        async_client.connect (
                                dispatcher, addr, timeout, socket.AF_INET
                                )
                                
        resolve (name, connect_or_close)
        return True


def reconnect (dispatcher, addr=None, timeout=None):
        dispatcher.closing = False
        return connect (
                dispatcher, 
                addr or dispatcher.addr, 
                timeout or dispatcher.client_timeout
                )


# conveniences for named TCP/IP connections

def dns_A_resolved (connections):
        "decorate a client abstraction with DNS name resolution"
        connections.client_resolved = ip_resolved
        connections.client_resolve = dns_A_resolve
        return connections


def Connections (timeout=3.0, precision=1.0, resolution=dns_A_resolved):
        "factor TCP/IP connections manager with DNS name resolution"
        return resolution (async_client.Connections (
                timeout, precision, socket.AF_INET
                ))

def Cache (timeout=3.0, precision=1.0, resolution=dns_A_resolved):
        "factor TCP/IP connections cache with DNS name resolution"
        return resolution (async_client.Cache (
                timeout, precision, socket.AF_INET
                ))

def Pool (
        Dispatcher, name, size=2, timeout=3.0, precision=1.0, 
        resolution=dns_A_resolved
        ):
        "factor TCP/IP connections pool with DNS name resolution"
        return resolution (async_client.Pool (
                Dispatcher, name, size, timeout, precision, socket.AF_INET
                ))
