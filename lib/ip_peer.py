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

import socket, random #, errno ?

from allegra import async_core


def my_ip ():
        return socket.gethostbyname (socket.gethostname ())

def udp_bind (dispatcher, ip=None, port=None):
        addr = ip or my_ip (), port or (
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
                # ? somehow connected ...
                assert None == dispatcher.log (
                        'bind ip="%s" port="%d"' % dispatcher.addr, 'debug'
                        )
                return True

        # not expected to raise anything else!


# small is beautifull
        