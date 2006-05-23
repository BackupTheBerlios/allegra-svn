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

"Metering and throttling decorators for async_core dispatchers"

import time

from allegra import async_loop


# Metering for stream and datagram sockets

def meter_recv (dispatcher, when):
        "decorate a stream transport with an input meter"
	dispatcher.ac_in_meter = 0
	dispatcher.ac_in_when = when
	metered_recv = dispatcher.recv
	def recv (buffer_size):
		data = metered_recv (buffer_size)
	        dispatcher.ac_in_meter += len (data)
		dispatcher.ac_in_when = time.time ()
	        return data
	        
	dispatcher.recv = recv

def meter_send (dispatcher, when):
        "decorate a stream transport with an output meter"
	dispatcher.ac_out_meter = 0
	dispatcher.ac_out_when = when
	metered_send = dispatcher.send
	def send (data):
		sent = metered_send (data)
	        dispatcher.ac_out_meter += sent
		dispatcher.ac_out_when = time.time ()
	        return sent
	        
	dispatcher.send = send

def meter_recvfrom (dispatcher, when):
        "decorate a datagram transport with an input meter"
        dispatcher.ac_in_meter = 0
        dispatcher.ac_in_when = when
        metered_recvfrom = dispatcher.recvfrom
        def recvfrom ():
                data, peer = metered_recvfrom ()
                dispatcher.ac_in_meter += len (data)
                dispatcher.ac_in_when = time.time ()
                return data, peer
                
        dispatcher.recvfrom = recvfrom

def meter_sendto (dispatcher, when):
        "decorate a datagram transport with an output meter"
        dispatcher.ac_out_meter = 0
        dispatcher.ac_out_when = when
	metered_sendto = dispatcher.sendto
	def sendto (self):
		sent = metered_sendto (data, peer)
	        dispatcher.ac_out_meter += sent
		dispatcher.ac_out_when = time.time ()
	        return sent

	dispatcher.sendto = sendto


# Inactivity Limits

def inactive_in (dispatcher, when):
        return not dispatcher.closing and dispatcher.connected and (
                when - dispatcher.ac_in_when
                ) > dispatcher.ac_inactive
        
def inactive_out (dispatcher, when):
        return not dispatcher.closing and dispatcher.connected and (
                when - dispatcher.ac_out_when
                ) > dispatcher.ac_inactive
        
def inactive (dispatcher, when):
        return not dispatcher.closing and dispatcher.connected and (
                when - max (
                        dispatcher.ac_in_when, dispatcher.ac_out_when
                        )
                ) > dispatcher.ac_inactive
        

# Throttling Decorators and Limits

def throttle_readable (dispatcher, when, Bps):
        "decorate a metered dispatcher with an input throttle"
	dispatcher.ac_in_throttle = Bps ()
	dispatcher.ac_in_throttle_when = when
	dispatcher.ac_in_throttle_Bps = Bps
	throttled_readable = dispatcher.readable
	def readable ():
		return (
			dispatcher.ac_in_meter < dispatcher.ac_in_throttle
			and throttled_readable ()
			)
	dispatcher.readable = readable
        
def throttle_in (dispatcher, when):
        "allocate input bandiwth to a throttled dispatcher"
	if dispatcher.ac_in_meter >= dispatcher.ac_in_throttle:
		dispatcher.async_limit_bytes_in += int ((
			when - max (
				dispatcher.ac_in_when,
				dispatcher.ac_in_throttle_when
				)
			) * dispatcher.ac_in_throttle_Bps ())
	dispatcher.ac_in_throttle_when = when
        return False

        #
        # when the dispatcher exceeded its limit, allocate bandwith at a given
        # rate for the period between "when" - approximatively but steadily
        # "now" - and the last I/O or the last allocation, which ever comes
        # later. in effect it grants the dispatcher the bandwith it is entitled
        # to for the immediate past.
	#
	# the async_throttle_in method is supposed to be called by a
	# periodical defered. for peers with long-lived dispatchers it is
	# faster to periodically allocate bandwith than to do it whenever 
	# we send or receive, or every time we check for readability or 
	# writability.


def throttle_writable (dispatcher, when, Bps):
        "decorate a metered dispatcher with an output throttle"
	dispatcher.ac_out_throttle = Bps ()
	dispatcher.ac_out_throttle_when = when
	dispatcher.ac_out_throttle_Bps = Bps
	throttled_writable = dispatcher.writable
	def writable ():
		return (
			dispatcher.ac_out_meter < dispatcher.ac_out_throttle
			and throttled_writable ()
			)
	dispatcher.writable = writable

def throttle_out (dispatcher, when):
        "allocate output bandiwth to a throttled dispatcher"
	if dispatcher.ac_out_meter >= dispatcher.ac_out_throttle:
		dispatcher.async_limit_bytes_out += int ((
			when - max (
				dispatcher.ac_out_when,
				dispatcher.ac_out_throttle_when
				)
			) * dispatcher.ac_out_throttle_Bps ())
	dispatcher.ac_out_throttle_when = when	
        return False
	

def throttle (dispatcher, when):
        "allocate I/O bandiwth to a throttled dispatcher"
        throttle_in (dispatcher, when)
        throttle_out (dispatcher, when)
        return False


# Limit recurrence factory

def limit_schedule (dispatcher, when, interval, limit, unlimit):
        # set the limit flag down
        dispatcher.limit_stop = False
        def scheduled (when):
                if dispatcher.closing or dispatcher.limit_stop:
                        # closing or limit flag raised, remove
                        unlimit (dispatcher)
                        return
                
                if limit (dispatcher, when):
                        # limit overflowed, remove and handle close
                        unlimit (dispatcher)
                        dispatcher.handle_close ()
                        return
                
                # recur at interval
                return (when + interval, scheduled)
        
        async_loop.async_schedule (when + interval, scheduled)

        # I like that one (nested namespaces rule ,-)

# Conveniences: ready-made metering and throttling

# a few more limits

def limit_in (dispatcher, when):
        return (
                inactive_in (dispatcher, when) or 
                throttle_in (dispatcher, when)
                )

def limit_out (dispatcher, when):
        return (
                inactive_out (dispatcher, when) or 
                throttle_out (dispatcher, when)
                )

def limit (dispatcher, when):
        return (
                inactive (dispatcher, when) or 
                throttle (dispatcher, when)
                )
                
# for stream transport

def limit_recv (dispatcher, interval, timeout, Bps):
        "meter recv and throttle readable, schedule throttling in"
        when = time.time ()
        dispatcher.ac_inactive = timeout
        dispatcher.ac_in_throttled = (dispatcher.recv, dispatcher.readable)
        meter_recv (dispatcher, when)
        throttle_readable (dispatcher, when, Bps)
        limit_schedule (
                dispatcher, when, interval, limit_in, unlimit_recv
                )

def unlimit_recv (dispatcher):
        "unmeter recv and unthrottle readable"
        dispatcher.recv, dispatcher.readable = dispatcher.ac_in_throttled
        del dispatcher.ac_in_throttled, dispatcher.ac_in_throttle_Bps 

def limit_send (dispatcher, interval, timeout, Bps):
        "meter send and throttle writable, schedule throttling out"
        when = time.time ()
        dispatcher.ac_inactive = timeout
        dispatcher.ac_out_throttled = (dispatcher.send, dispatcher.writable)
        meter_send (dispatcher, when)
        throttle_writable (dispatcher, when, Bps)
        limit_schedule (
                dispatcher, when, interval, limit_out, unlimit_send
                )

def unlimit_send (dispatcher):
        "unmeter send and unthrottle writable"
        dispatcher.send, dispatcher.writable = dispatcher.ac_out_throttled
        del dispatcher.ac_out_throttled, dispatcher.ac_out_throttle_Bps 

def limit_stream (dispatcher, interval, timeout, inBps, outBps):
        "meter and throttle stream I/O, schedule throttling"
        when = time.time ()
        dispatcher.ac_inactive = timeout
        dispatcher.ac_in_throttled = (dispatcher.recv, dispatcher.readable)
        meter_recv (dispatcher, when)
        throttle_readable (dispatcher, when, inBps)
        dispatcher.ac_out_throttled = (dispatcher.send, dispatcher.writable)
        meter_send (dispatcher, when)
        throttle_writable (dispatcher, when, inBps)
        limit_schedule (
                dispatcher, when, interval, limit, unlimit_stream
                )

def unlimit_stream (dispatcher):
        "unmeter and unthrottle stream I/O"
        dispatcher.recv, dispatcher.readable = dispatcher.ac_in_throttled
        del dispatcher.ac_in_throttled, dispatcher.ac_in_throttle_Bps 
        dispatcher.send, dispatcher.writable = dispatcher.ac_out_throttled
        del dispatcher.ac_out_throttled, dispatcher.ac_out_throttle_Bps 

# for datagram transport

def limit_recvfrom (dispatcher, interval, timeout, Bps):
        "meter recvfrom and throttle readable, schedule throttling in"
        when = time.time ()
        dispatcher.ac_inactive = timeout
        meter_recvfrom (dispatcher, when)
        throttle_readable (dispatcher, when, Bps)
        limit_schedule (
                dispatcher, when, interval, limit_in, unlimit_recvfrom
                )

def unlimit_recvfrom (dispatcher):
        "unmeter recvfrom and unthrottle readable"
        dispatcher.recvfrom, dispatcher.readable = dispatcher.ac_out_throttled
        del dispatcher.ac_in_throttled, dispatcher.ac_in_throttle_Bps 

def limit_sendto (dispatcher, interval, timeout, Bps):
        "meter sendto and throttle writable, schedule throttling out"
        when = time.time ()
        dispatcher.ac_inactive = timeout
        meter_sendto (dispatcher, when)
        throttle_writable (dispatcher, when, Bps)
        limit_schedule (
                dispatcher, when, interval, limit_out, unlimit_sendto
                )

def unlimit_sendto (dispatcher):
        "unmeter sendto and unthrottle writable"
        dispatcher.sendto, dispatcher.writable = dispatcher.ac_out_throttled
        del dispatcher.ac_out_throttled, dispatcher.ac_out_throttle_Bps 

def limit_datagram (dispatcher, interval, timeout, inBps, outBps):
        "meter and throttle datagram I/O, schedule throttling"
        when = time.time ()
        dispatcher.ac_inactive = timeout
        dispatcher.ac_in_throttled = (dispatcher.recv, dispatcher.readable)
        meter_recvfrom (dispatcher, when)
        throttle_readable (dispatcher, when, inBps)
        dispatcher.ac_out_throttled = (dispatcher.send, dispatcher.writable)
        meter_sendto (dispatcher, when)
        throttle_writable (dispatcher, when, inBps)
        limit_schedule (
                dispatcher, when, interval, limit, unlimit_datagram
                )

def unlimit_datagram (dispatcher):
        "unmeter and unthrottle datagram I/O"
        dispatcher.recvfrom, dispatcher.readable = dispatcher.ac_in_throttled
        del dispatcher.ac_in_throttled, dispatcher.ac_in_throttle_Bps 
        dispatcher.sendto, dispatcher.writable = dispatcher.ac_out_throttled
        del dispatcher.ac_out_throttled, dispatcher.ac_out_throttle_Bps 

# Note about this implementation
#
# other kind of limits - like an absolute limit on the maximum i/o or
# duration per dispatcher - should be implemented in the final class.
#
#
# The Case for Throttling
#
# Asynchat allows to save server's resources by limiting the i/o buffers
# but for a peer on the edges of the network, the bottleneck is bandwith
# not memory. Compare the 16KBps upload limit of a low-end connection with
# the 512MB of RAM available in most PCs those days ... it would take nine
# hours to upload that much data in such small pipe.
#
# It is a basic requirement for a peer to throttle its traffic to a fraction
# of the bandwith generaly available. Because there *are* other applications
# and system functions that need a bit of bandwith, and peer application tend
# to exhaust network resources pretty fast.
#
