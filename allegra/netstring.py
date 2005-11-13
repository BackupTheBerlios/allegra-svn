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
#

"""This module implements six functions for netstrings encoding and decoding,
as well as a usefull shell pipe. 

SINOPSYS

	netstring.py [command] [buffer] < stdin 1> stdout 2> stderr

	If not specified, the default command is 'decode'. The second 
	optional argument is the size of the decoder's buffer.

EXAMPLES

Decode and beautify a stream of netstrings:

	netstring.py decode < netstrings.net 1> netlines.txt

Encode a stream of lines as safe netstrings:

	netstring.py encode < lines.txt 1> safe.net
	
No exceptions are catched and their tracebacks are printed to STDERR."""


__author__ = 'Laurent A.V. Szyster <contact@laurentszyster.be>'


import exceptions


def netstring_encode (i):
	"""encode an instance as a netstring, use its __str__ or __repr__ 
	method to get the 8-bit byte string representation of the instance."""
	try:
		s = i.__str__ ()
	except:
		s = i.__repr__ ()
	return '%d:%s,' % (len (s), s)


def netstrings_encode (i):
	"encode an sequence of 8-bit byte strings as netstrings"
	return ''.join (['%d:%s,' % (len (s), s) for s in i])


def netstrings_buffer (buffer):
	"decode the netstrings found in the buffer, append garbage at the end"
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
	"decode the netstrings found in the buffer and return a list"
	return list (netstrings_buffer (buffer))


class NetstringsError (exceptions.Exception): pass


def netstrings_pipe (more):
	"""decode the stream of netstrings produced by more (), 
	raise a NetstringsError exception on protocol failure or
	StopIteration when the producer is exhausted"""
	buffer = more ()
	while buffer:
		pos = buffer.find (':')
		length = buffer[:pos]
		try:
			next = pos + int (length) + 1
		except:
			raise NetstringsError, '1 not a digit'
	
		while next >= len (buffer):
			data = more ()
			if data:
				buffer += data
			else:
				raise NetstringsError, '2 end of buffer'
		
		if buffer[next] == ',':
			yield buffer[pos+1:next]

		else:
			raise NetstringsError, '3 missing coma'

		buffer = buffer[next+1:]
		if buffer.isdigit ():
			buffer += more ()


def netlines (encoded, indent=''):
	"""Recursively beautify a netstring for display"""
	netstrings = netstrings_decode (encoded)
	if len (netstrings) > 1:
		lines = ''.join (
			[netlines (e, indent+'  ') for e in netstrings]
			)
		return '%s%d:\n%s%s,\n' % (
			indent, len (encoded), lines, indent
			)
			
	return '%s%d:%s,\n' % (indent, len (encoded), encoded)


def netoutlines (encoded, format='%s\n'):
	"""Recursively beautify a netstring as a CRLF outline"""
	netstrings = netstrings_decode (encoded)
	if len (netstrings) > 1:
		return ''.join (
			[netoutlines (e, '  '+format) for e in netstrings]
			)
			
	return format % encoded


if __name__ == '__main__':
        import sys
        assert None == sys.stderr.write (
                'Allegra Netstrings'
                ' - Copyright 2005 Laurent A.V. Szyster'
                ' | Copyleft GPL 2.0\n'
                )
        if len (sys.argv) > 1:
        	command = sys.argv[1]
 	else:
		command = 'decode'
 	if command == 'decode':
 		if len (sys.argv) > 2:
 			try:
 				buffer_size = int (sys.argv[2])
			except:
				sys.stderr.write ('2 invalid buffer size\n')
				sys.exit (2)
				
		else:
	 		buffer_size = 4096
		def more ():
			return sys.stdin.read (buffer_size)
		for n in netstrings_pipe (more):
			sys.stdout.write (netlines (n) + '\n')
	elif command == 'encode':
		for line in sys.stdin.xreadlines ():
			sys.stdout.write (
				'%d:%s,' % (len (line)-1, line[:-1])
				)
	else:
		sys.stderr.write ('1 invalid command\n')
		sys.exit (1)
		
	sys.exit (0)

# Note about this implementation
#
# Programs usually starts as simple shell scripts that dump some their 
# output to STDOUT and errors to STDERR, like this:
#	
#	script < input 1> output 2> errors
#
# probably consuming input from STDIN. Also, application modules should 
# provide such simple pipes to test separately the functions implemented.
#
# Generally such program consume and produce lines delimited by CR or CRLF,
# using the readline and writeline interfaces provided by the development 
# environemnt. In Python the infamous print statement or the sys.stdin,
# -out or -err files methods.
#
# However, CR or CRLF lines as an encoding for I/O are too simple. This is
# a well-known shortcoming of the MIME protocols and netstring protocols like 
# QMTP have proved to be more efficient and safer than SMTP, for instance.
