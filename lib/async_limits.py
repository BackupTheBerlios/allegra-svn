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

import time


# Add asynchronous limits to a UDP dispatcher or a TCP channel

def async_limit_recv (channel, when):
	channel.async_bytes_in = 0
	channel.async_when_in = when
	recv = channel.recv
	def async_limit_recv (buffer_size):
		data = recv (buffer_size)
	        channel.async_bytes_in += len (data)
		channel.async_when_in = when
	        return data
	        
	channel.recv = async_limit_recv

def async_limit_recvfrom (channel, when):
	recvfrom = channel.recvfrom
	def async_limit_recvfrom ():
		data, peer = recvfrom ()
	        channel.async_bytes_in += len (data)
		channel.async_when_in = when
	        return data, peer
	        
	channel.recvfrom = async_limit_recvfrom

def async_limit_send (channel, when):
	channel.async_bytes_out = 0
	channel.async_when_out = when
	send = channel.send
	def async_limit_send (data):
		sent = send (data)
	        channel.async_bytes_out += sent
		channel.async_when_out = when
	        return sent
	        
	channel.send = async_limit_send

def async_limit_sendto (channel, when):
	sendto = channel.sendto
	def async_limit_sendto (self):
		sent = sendto (data, peer)
	        channel.async_bytes_out += sent
		channel.async_when_out = when
	        return sent

	channel.sendto = async_limit_sendto
	

def FourKBps ():
	return 4096 # ac_in_buffer_size


def async_throttle_in (channel, when, Bps=FourKBps):
	channel.async_limit_bytes_in = Bps ()
	channel.async_throttle_in_when = when
	channel.async_throttle_in_Bps = Bps
	readable = channel.readable
	def async_throttle_readable ():
		return (
			channel.async_bytes_in < channel.async_limit_bytes_in 
			and readable ()
			)
	channel.readable = async_throttle_readable
	
def async_throttle_in_defer (channel, when):
	# when the channel exceeded its limit, allocate bandwith at a given
	# rate for the period between "when" - approximatively but steadily
	# "now" - and the last I/O or the last allocation, which ever comes
	# later. in effect it grants the channel the bandwith it is entitled
	# to for the immediate past.
	#
	if channel.async_bytes_in >= channel.async_limit_bytes_in:
		channel.async_limit_bytes_in += int ((
			when - max (
				channel.async_when_in,
				channel.async_throttle_in_when
				)
			) * channel.async_throttle_in_Bps ())
	channel.async_throttle_in_when = when
	#
	# the async_throttle_in method is supposed to be called by a
	# periodical defered. for peers with long-lived channels it is
	# faster to periodically allocate bandwith than to do it whenever 
	# we send or receive, or every time we check for readability or 
	# writability.


def async_throttle_out (channel, when, Bps=FourKBps):
	channel.async_limit_bytes_out = Bps ()
	channel.async_throttle_out_when = when
	channel.async_throttle_out_Bps = Bps
	writable = channel.writable
	def async_throttle_writable ():
		return (
			channel.async_bytes_out < channel.async_limit_bytes_out
			and writable ()
			)
	channel.writable = async_throttle_writable
	
def async_throttle_out_defer (channel, when):
	if channel.async_bytes_out >= channel.async_limit_bytes_out:
		channel.async_limit_bytes_out += int ((
			when - max (
				channel.async_when_out,
				channel.async_throttle_out_when
				)
			) * channel.async_throttle_out_Bps ())
	channel.async_throttle_out_when = when	
	

# Note about this implementation
#
# other kind of limits - like an absolute limit on the maximum i/o or
# duration per channel - should be implemented in the final class.
#
#
# The Case for Throttling
#
# Asynchat allows to save server's resources by limiting the i/o buffers
# but for a peer on the edges of the network, the bottleneck is bandwith
# not memory. Compare the 16KBps upload limit of a cable connection with
# the 256MB of RAM available in most PCs those days ... it would take 4,5
# hours to upload that much data in such small pipe.
#
# It is a basic requirement for a peer to throttle its traffic to a fraction
# of the bandwith generaly available. Because there *are* other applications
# and system functions that need a bit of bandwith, and peer application tend
# to exhaust network resources.
