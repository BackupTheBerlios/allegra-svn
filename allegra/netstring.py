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

from exceptions import Exception

# the netstring definition, a few netstrings encoders and one usefull
# decoder for buffered sequences of netstrings.

def netstring_encode (i):
	try:
		s = '%s' % (i,)
	except:
		s = '%r' % (i,)
	return '%d:%s,' % (len (s), s)


def netstrings_encode (n):
	return ''.join (['%d:%s,' % (len (s), s) for s in n])


def netstrings_decoder (buffer):
	while buffer:
		pos = buffer.find (':')
		try:
			next = pos + int (buffer[:pos]) + 1
		except:
			yield buffer
			
			break
	
		if next >= len (buffer):
			yield buffer

			break
		
		if buffer[next] == ',':
			yield buffer[pos+1:next]

		else:
			yield buffer
			
			break

		buffer = buffer[next+1:]


def netstrings_decode (buffer):
	return list (netstrings_decoder (buffer))


# Netstrings Collector and Generator

class Netstring_collector:
	
	# a simple netstring collector to mixin with asynchat
	
	collector_is_simple = 0
	
	def __init__ (self):
		self.netstring_collector = ''
		self.set_terminator (':')

	def collect_incoming_data (self, data):
		self.netstring_collector += data

	def found_terminator (self):
		if self.get_terminator () != ':':
			if self.netstring_collector[-1] != ',':
				self.nestring_collector_error ()
				return
				
			self.netstring_collector_continue (
				self.netstring_collector[:-1]
				)
			self.netstring_collector = ''
			self.set_terminator (':')
			return
			
		if self.netstring_collector.isdigit ():
			self.set_terminator (
				int (self.netstring_collector) + 1
				)
			self.netstring_collector = ''
			return

		self.nestring_collector_error ()

	# def nestring_collector_continue (self):
		
	# def nestring_collector_error (self):
		

class NetstringsError (Exception): pass


def netstrings_generator (more):
	# a simple netstring generator "wrapping" a producer method
	buffer = more ()
	while buffer:
		pos = buffer.find (':')
		length = buffer[:pos]
		try:
			next = pos + int (length) + 1
		except:
			raise NetstringsError, \
				'1 not a digit at the beginning: %s' % length
	
		while next >= len (buffer):
			data = more ()
			if data:
				buffer += data
			else:
				raise NetstringsError, \
					'2 premature end of buffer'
		
		if buffer[next] == ',':
			yield buffer[pos+1:next]

		else:
			raise NetstringsError, \
				'3 missing coma at the end'

		buffer = buffer[next+1:]
		if buffer.isdigit ():
			buffer += more ()


def netlines (encoded, indent=''):
	netstrings = netstrings_decode (encoded)
	if len (netstrings) > 1:
		encoded = ''.join (
			[netlines (e, indent+'  ') for e in netstrings]
			)
		return '%s%d:\n%s%s,\n' % (
			indent, len (encoded), encoded, indent
			)
			
	return '%s%d:%s,\n' % (
		indent, len (encoded), encoded
		)


# The Netstring Beauty Validator

if __name__ == '__main__':
        import sys
        assert None == sys.stderr.write (
                'Allegra Netstrings'
                ' - Copyright 2005 Laurent A.V. Szyster'
                ' | Copyleft GPL 2.0\n'
                )
	for n in netstrings_generator (lambda: sys.stdin.read (4096)):
		sys.stdout.write (netlines (n) + '\n')
        #
	# the simpler synchronous pipe, adding a \n for marginal readability
	# of a netstring dump.
        #
        # use -OO to prevent Copyright Message and benchmark

#
# Note about this implementation
#
# I look back with shame on the earlier decoder, I wish there was
# not even a single bit left of it in this digital age. Yet that
# simple generator redeems those early days.
#
# Yet, the interface was (allmost) right from the start: tolerate
# garbage at the end to allways return at least en singleton. The
# "old" code will however be usefull for good-old C optimization.
#
# So, all experiences eventually are usefull ;-)
#
