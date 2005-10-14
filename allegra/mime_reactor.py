# Copyright (C) 2005 Laurent A.V. Szyster
# 
# This library is free software; you can redistribute it and/or modify
# it under the terms of version 2.1 of the GNU Lesser General Public
# License as published by the Free Software Foundation.
# 
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307
# USA

""

from allegra.finalization import Finalization
from allegra.reactor import Buffer_reactor
from allegra.mime_producer import MIME_producer
from allegra.mime_collector import MIME_collector


class MIME_reactor (MIME_collector, MIME_producer, Finalization):

	__init__ = MIME_collector.__init__
		
	def mime_collector_continue (self):
		body = Buffer_reactor ()
		MIME_producer.__init__ (
			self, self.mime_collector_headers, body
			)
		return body
			

if __name__ == '__main__':
	import sys
	sys.stderr.write (
		'Allegra MIME Validator'
		' - Copyright 2005 Laurent A.V. Szyster'
                ' | Copyleft GPL 2.0\n...\n'
                )
	def mime_collector_finalize (collector):
		while 1:
			data = collector.mime_collector_body.more ()
			if data:
				sys.stdout.write (data)
			else:
				break
				
	mime_reactor = MIME_reactor ()
	mime_reactor.mime_collector_finalize = mime_collector_finalize
	simple_collector = Simple_collector (mime_reactor)
	while 1:
		data = sys.stdin.read (4096)
		if data:
			simple_collector.collect_incoming_data (data)
		else:
			break
	
	# Simply pipes a MIME or MIME/MULTIPART message from STDIN to STDOUT
	# collecting its parts and reproducing the input. Finalization(s) are
	# dumped to STDERR.
			
# A MIME reactor that uses a Buffer_reactor to proxy the collected
# headers and body to an asynchat channel simply by pushing the
# reactor in its producer_fifo queue. It may be used to proxy any
# kind of MIME protocols, including HTTP, SMTP, POP3, etc.
#
# The lifecycle of a one way MIME proxy is usally this one:
#
#	0. instanciated, completed and set as its mime_body_collector
#          by the MIME collector channel, with a Buffer_reactor as body
#	1. pushed to the MIME producer channel with its mime body
#	   producer set to its mime_body_collector
#	2. dereferenced by the collector channel when collected
#	3. dereferenced by the producer channel when produced
#	4. finalized
#
# In the case of a two-way HTTP proxy, the finalization of a request
# reactor consists in instanciating a response reactor and pushing
# it back to the original collector channel.
#
# A MIME server can also be considered a one-way proxy using the same
# channel to collect requests from and produce responses to ;-)
#
#	0. instanciated, completed and and set as its mime_body_collector
#          by the MIME collector channel if there is a body to collect
#	1. pushed to the server channel
#	2. dereferenced by the server channel when collected
#	3. dereferenced by the server channel when produced
#	4. finalized
#
# The full implication of that original design of a MIME server, is
# that you can pipeline HTTP/1.1 requests like POST and PUT and still
# produce the response headers before the request's body as been
# collected.
#
# Of course a MIME client can be viewed in the same perspective:
#
#	0. instanciated and completed by a MIME client channel
#	1. pushed to the client channel
#	2. dereferenced by the client channel when produced
#	3. dereferenced by the client channel when collected
#	4. finalized
#

