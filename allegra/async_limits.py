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

from time import time

class Async_limit_out:
	
	# TODO: fix the Async_limit_out first then copy here

	async_bytes_out = async_when_out = 0

        def async_limit_out (self, sent):
                self.async_bytes_out += sent
                return sent

	def async_limit_send (self):
		self.send = (
			lambda data, c=self, s=self.send: c.async_limit_out (s (data))
			)

	def async_limit_sendto (self):
		self.sendto = (
			lambda data, peer, c=self, s=self.sendto:
			c.async_limit_out (s (data, peer))
			)


class Async_limit_in:

	# a generic limit for UDP dispatcher and TCP channels
	#
	# TODO: fix a bug in async_when_in that triggers "<inactive/>"
	
	async_bytes_in = async_when_in = 0

        def async_limit_in (self, received):
		self.async_bytes_in += len (received)
		self.async_when_in = time ()
		return received

	def async_limit_recv (self):
		self.recv = (
			lambda bytes, c=self, r=self.recv: c.async_limit_in (r (bytes))
			)

        def async_limit_from (self, received, peer):
		self.async_bytes_in += len (received)
		self.async_when_in = time ()
		return received, peer

	def async_limit_recvfrom (self):
		self.recvfrom = (
			lambda c=self, r=self.recvfrom: c.async_limit_from (r ())
			)


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

class Async_throttle_out:

	async_throttle_out_Bps = lambda s: 4096 # throttle output to 4 KBps

	def async_limit_write (self):
		self.async_limit_bytes_out = 1
		self.async_throttle_out_when = time ()
		self.writable = (
			lambda c=self, w=self.writable: (
				c.async_bytes_out < c.async_limit_bytes_out and w ()
				)
			)

	def async_throttle_out (self, when):
		# when the channel exceeded its limit, allocate bandwith at a given
		# rate for the period between "when" - approximatively but steadily
		# "now" - and the last I/O or the last allocation, which ever comes
		# later. in effect it grants the channel the bandwith it is entitled
		# too for the immediate past.
		#
		if self.async_bytes_out >= self.async_limit_bytes_out:
			self.async_limit_bytes_out += int ((
				when - max (
					self.async_when_out,
					self.async_throttle_out_when
					)
				) * self.async_throttle_out_Bps ())
		self.async_throttle_out_when = when
		#
		# the async_throttle_out method is supposed to be called by a
		# periodical defered. for peers with relatively few client it is
		# however faster to periodically allocate bandwith than to do it
		# whenever we send or receive, or every time we check for
		# readability or writability.


class Async_throttle_in:

	async_throttle_in_Bps = lambda s: 4096  # throttle input to 4 KBps

	def async_limit_read (self):
		self.async_limit_bytes_in = 1
		self.async_throttle_in_when = time ()
		self.readable = (
			lambda c=self, r=self.readable: (
				c.async_bytes_in < c.async_limit_bytes_in and r ()
				)
			)

	def async_throttle_in (self, when):
		if self.async_bytes_in >= self.async_limit_bytes_in:
			self.async_limit_bytes_in += int ((
				when - max (
					self.async_when_in,
					self.async_throttle_in_when
					)
				) * self.async_throttle_in_Bps ())
		self.async_throttle_in_when = when


# other kind of limits - like an absolute limit on the maximum i/o or
# duration per channel - should be implemented in the final class.
