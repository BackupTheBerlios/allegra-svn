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

def bind (dispatcher, ip=None, port=None):
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


class Bind (async_core.Dispatcher):
        
        udp_peer_fifo = None
        
	def __repr__ (self):
		return 'udp-peer id="%x"' % id (self)

	def writable (self):
		return not (not (self.udp_peer_fifo))
                #
                # funny isn't:
                #
                #     not (not (None)) == False
                #     not (not (deque ())) == False
                #
                # but
                #
                #     not (not (deque ((1,)))) == True
                #
                # fast and very practical

	# ECONNRESET, ENOTCONN, ESHUTDOWN
	#
        # catch all socket exceptions for reading and writing, this is UDP
        # and the protocol implementation derived from this dispatcher
        # should handle error without closing the channel.
	#
	# basically, I know little about how UDP sockets behave (less how 
	# they do on various systems ;-)

	def handle_read (self):
		# to subclass
		data, peer = self.recvfrom ()
		if peer != None:
			assert None == self.log (
				'recvfrom ip="%s" port"%d" bytes="%d"' % (
					peer[0], peer[1], len (data)
					), 'debug'
				)
		else:
			assert None == self.log ('recvfrom', 'debug')


        def udp_peer_push (self, datagram_to):
                try:
                        self.udp_peer_fifo.append (datagram_to)
                except:
                        self.udp_peer_fifo = [datagram_to]
                #
                # use a simple list for short fifo queue, you don't want
                # to build up big queues for UDP applications! if it slows
                # down because of large queues, there's a problem with the
                # application, the API can't do any good to handle that.

        def handle_write (self):
                sendto = self.sendto
                for datagram_to in self.udp_peer_fifo: 
                        sendto (*datagram_to)
                self.udp_peer_fifo = None
                #
                # the "gist" of that default implementation, is that it
                # allows to use sendto directly (UDP is not blocking by
                # nature, packets are dropped, it is unreliable by design,
                # something has to give in ...) but also enables the
                # application to start queuing datagrams whenever its 
                # meters indicate levels of resource shortage (ymmv).
                #
                # the purpose is to take advantage of all those meters,
                # limits and throttlers for UDP peers too, because on
                # a modest 500Mhz running Debian GNU/Linux, it's too easy to
                # saturate the network with datagrams that start dropping
                # fast and in batches at the first router. also, those
                # datagrams may be polled from synchronized API (like a 
                # file transfered or a compression process distributed)
                # eventually blocking. 
                #
                # if you can slow down a bit sometimes, it may be possible 
                # to make the most out of your bandwith. if you have more
                # upload bandwith than you can send and no router to drop,
                # never put the breaks and use sendto directly at all times.

        #
        # small is beautifull

# TODO: add a UDP pipeline implementation that behaves like asynchat?