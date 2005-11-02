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

from allegra.collector import Simple_collector, Length_collector
from allegra.mime_collector import Chunk_collector


def http_collector_continue (self, collector):
	# decide wether and wich collector wrappers are needed
        if self.mime_collector_headers.get (
		'transfer-encoding', ''
		).lower () == 'chunked':
		# HTTP/1.1 only
		if not collector.collector_is_simple:
			collector = Simple_collector (collector)
		self.mime_collector_body = Chunk_collector (
			collector,
			self.set_terminator,
			self.mime_collector_headers
			)
	else:
		# HTTP/1.0 mostly
		content_length = self.mime_collector_headers.get (
			'content-length'
			)
		if content_length:
			if collector.collector_is_simple:
				self.mime_collector_body = collector
				self.set_terminator (int (content_length))
			else:
				self.mime_collector_body = Length_collector (
					collector, int (content_length)
					)
		else:
			# HTTP/1.0 connection closed
			self.mime_collector_body = collector
			self.set_terminator (None)


# URLencoded form data collector


# TODO: add charset decoding to UNICODE, with RFC-3023 and "bozo" detection
#
#	http://feedparser.org/docs/character-encoding.html
#
