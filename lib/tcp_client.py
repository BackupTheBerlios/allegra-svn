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


def connect (
        dispatcher, name, timeout, 
        resolved=dns_client.ip_resolved, resolve=resolve_dns_A
        ):
        "resolve and maybe connect a dispatcher, close on error"
        if resolved (name):
                if not async_client.connect (
                        dispatcher, name, timeout, socket.AF_INET
                        ):
                        dispatcher.handle_close ()
                        return False
                
                return True

        if resolve == None:
                dispatcher.handle_close ()
                return False
        
        def resolve (addr):
                if addr == None or not async_client.connect (
                        dispatcher, addr, timeout, socket.AF_INET
                        ):
                        dispatcher.handle_close ()
        client_resolve (name, resolve)
        return True


def dns_A_resolved (connections, resolver=None):
        if resolver == None:
                resolver = DNS_client (dns_servers ())
        def async_client_resolve (name, resolve):
                def dns_resolve (resolved):
                        if resolved.dns_resources:
                                resolve (resolved.dns_resources[0])
                        else:
                                resolve (None)
                resolver.dns_resolve ((name, 'A'), dns_resolve)
        
        connections.client_resolved = ip_resolved
        connections.client_resolve = async_client_resolve

# conveniences for named TCP/IP connections

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