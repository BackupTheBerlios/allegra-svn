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

class MIME_producer:
	
	mime_producer_lines = mime_producer_body = None
	
	def __init__ (self, lines_or_headers=None, body=None):
		if lines_or_headers != None:
			if type (lines_or_headers) == type ([]):
				self.mime_producer_lines = lines_or_headers
			else:
				self.mime_producer_lines = [
					'%s: %s\r\n' % (n, v)
					for n,v in lines_or_headers.items ()
					]
				self.mime_producer_lines.append ('\r\n')
		self.mime_producer_body = body
		
	def producer_stalled (self):
		return (
			self.mime_producer_body == None or
			self.mime_producer_body.producer_stalled ()
			)

	def more (self):
		if self.mime_producer_lines:
			data = ''.join (self.mime_producer_lines)
			self.mime_producer_lines = None
			return data

		if self.mime_producer_body:
			return self.mime_producer_body.more ()
			
		return ''