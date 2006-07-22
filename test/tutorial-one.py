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

"http://laurentszyster.be/blog/tutorial-one/"

# A Simple Client

from allegra import (
    async_loop, async_chat, collector, async_client
    )

dispatcher = async_chat.Dispatcher ()
if async_client.connect (
    dispatcher, ('66.249.91.99', 80), 3
    ):
    dispatcher.async_chat_push (
        "GET / HTTP/1.1\r\n"
        "host: 66.249.91.99\r\n"
        "Connection: close\r\n"
        "\r\n"
        )
    collector.bind (
        dispatcher, collector.LOGINFO
        )
async_loop.dispatch ()


# Adding Features

from allegra import (
    finalization, async_limits, synchronized
    )

dispatcher = async_chat.Dispatcher ()
if async_client.connect (
    dispatcher, ('66.249.91.99', 80), 3
    ):
    dispatcher.async_chat_push (
        "GET / HTTP/1.1\r\n"
        "host: 66.249.91.99\r\n"
        "Connection: close\r\n"
        "\r\n"
        )
    collector.bind (
        dispatcher,
        synchronized.File_collector ('response.txt')
        )
    async_limits.limit_recv (
        dispatcher, 3, 1, (lambda: 1<<13)
        )
    dispatcher.finalization = (
        lambda finalized: finalized.log (
            'bytes in="%d"' % finalized.ac_in_meter
            )
        )
    del dispatcher
async_loop.dispatch ()
finalization.collect ()


# Decouple A Lot

dispatcher = async_chat.Dispatcher ()
dispatcher.finalization = (
    lambda finalized: finalized.log (
        'bytes in="%d"' % finalized.ac_in_meter
        )
    )
dispatcher.async_chat_push (
    "GET / HTTP/1.1\r\n"
    "host: 66.249.91.99\r\n"
    "Connection: close\r\n"
    "\r\n"
    )
collector.bind (
    dispatcher,
    synchronized.File_collector ('response.txt')
    )
async_limits.limit_recv (
    dispatcher, 3, 1, (lambda: 1<<13)
    )
async_client.connect (
    dispatcher, ('66.249.91.99', 80), 3
    )
del dispatcher
async_loop.dispatch ()
finalization.collect ()