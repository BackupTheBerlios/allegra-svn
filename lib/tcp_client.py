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

from allegra import async_client, dns_client


def dns_A_resolve (name, resolve):
        def dns_resolve (resolved):
                if resolved.dns_resources:
                        resolve (resolved.dns_resources[0])
                else:
                        resolve (None)
        dns_client.RESOLVER ((name, 'A'), dns_resolve)


def connect (
        dispatcher, addr, timeout, 
        resolved=dns_client.ip_resolved, resolve=dns_A_resolve
        ):
        "resolve and maybe connect a dispatcher, close on error"
        assert not dispatcher.connected
        ip = resolved (addr)
        if ip != None:
                return async_client.connect (
                        dispatcher, addr, timeout, socket.AF_INET
                        )

        if resolve == None:
                dispatcher.handle_close ()
                return False
        
        def connect_or_close (ip):
                if ip == None:
                        dispatcher.handle_close ()
                else:
                        async_client.connect (
                                dispatcher, (ip, addr[1]), timeout, 
                                socket.AF_INET
                                )
                                
        resolve (addr[0], connect_or_close)
        return True


# conveniences for named TCP/IP connections

def dns_A_resolved (connections):
        assert dns_client.RESOLVER != None
        connections.client_resolved = dns_client.ip_resolved
        connections.client_resolve = dns_A_resolve


def Connections (
        timeout, precision, 
        resolution=dns_A_resolved
        ):
        connections = async_clientConnections (
                timeout, precision, socket.AF_INET
                )
        connections.client_resolved = resolution (connections)
        return connections

def Cache (
        Dispatcher, timeout, precision, 
        resolution=dns_A_resolved
        ):
        connections = async_client.Connections (
                Dispatcher, timeout, precision, socket.AF_INET
                )
        connections.client_resolved = resolution (connections)
        return connections

def Pool (
        Dispatcher, name, size, timeout, precision, 
        resolution=dns_A_resolved
        ):
        connections = async_client.Connections (
                Dispatcher, timeout, precision, socket.AF_INET
                )
        connections.client_resolved = resolution (connections)
        return connections

# 