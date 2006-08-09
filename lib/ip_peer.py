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

"http://laurentszyster.be/blog/ip_peer/"

import socket, random


def is_ip (name):
        "returns True if the name is a valid IPv4 address string"
        return len (tuple ((
                digit for digit in name.split ('.')
                if digit.isdigit () and -1 < int (digit) < 256
                ))) == 4


def in_addr_arpa (s):
        "reverse an IPv4 address string in the arpa address space"
        l = s.split ('.')
        l.reverse ()
        l.extend (('in-addr', 'arpa'))
        return '.'.join (l)
        

def ip2long (s):
        "convert IPv4 address string to a long integer"
        l = [long (n) for n in s.split ('.')]
        i = l.pop (0)
        while l:
                i = (i << 8) + l.pop (0)
        return i

def long2ip (i):
        "convert a long integer to an IPv4 address string"
        i, rest = divmod (i, 16777216)
        s = str (i)
        i, rest = divmod (rest, 65536)
        s = '%s.%d' % (s, i)
        i, rest = divmod (rest, 256)
        return '%s.%d.%d' % (s, i, rest)


def _host_ip ():
        "resolve the host IP address synchronously"
        return socket.gethostbyname (socket.gethostname ())

host_ip = _host_ip ()


local_network = ip2long ('127.0.0.0')
private_network_A = ip2long ('10.0.0.0')
private_network_C = ip2long ('192.168.0.0')

def is_local (ipl):
        "returns True if the IP long belongs to the IPv4 local network"
        return ipl | local_network == ipl

def is_private (ipl):
        "returns True if the IP long belongs to a IPv4 private network"
        return (
                (ipl | private_network_A == ipl) or 
                (ipl | private_network_C == ipl)
                )


def udp_bind (dispatcher, ip=None, port=None):
        """bind an async_core.Dispatcher () to an address and return True
        or handle_close and return False, maybe use the host IP and a random
        port if None are specified."""
        addr = ip or host_ip, port or (
                (abs (hash (random.random ())) >> 16) + 8192
                )
        try:
                dispatcher.create_socket (
                        socket.AF_INET, socket.SOCK_DGRAM
                        )
                dispatcher.bind (addr)
        except socket.error:
                dispatcher.loginfo_traceback ()
                if dispatcher.socket != None:
                        dispatcher.handle_close ()
                return False
        
        else:
                assert None == dispatcher.log (
                        'bind ip="%s" port="%d"' % dispatcher.addr, 'debug'
                        )
                return True


# 105 lines, with spacing, licence and docstrings: small is beautifull