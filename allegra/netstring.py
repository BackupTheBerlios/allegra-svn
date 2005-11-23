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

"""API

...

	>>> from allegra import netstring
	>>> netstring.encode (('A', 'B', 'CD'))
	'1:A,1:B,2:CD,'
	>>> tuple (netstring.decode ('1:A,1:B,2:CD,'))
	('A', 'B', 'CD')
	>>> tuple (netstring.decode (':A,1:B,2:CD,'))
	()
	>>> tuple (netstring.decode ('1:A,1:B,2:C'))
	('A', 'B')
	>>> def more ():
		return '1:A,1:B,2:CD,'
	>>> g = netstring.pipe (more)
	>>> g.next ()
	'A'
	>>> g.next ()
	'B'
	>>> g.next ()
	'CD'
	>>> g.next ()
	'A'
	
	
CLI

...

	netstring.py [command] [buffer] < stdin 1> stdout 2> stderr

If not specified, the default command is 'outline'. The second 
optional argument is the size of the decoder's buffer.

Validate a stream of netstrings:

	netstring.py decode < netstrings.net

Decode a stream of netstrings and beautify the output a text outline:

	netstring.py outline < netstrings.net 1> netlines.txt

Encode a stream of lines as safe netstrings:

	netstring.py encode < lines.txt 1> safe.net
	
No exceptions are catched and their tracebacks are printed to STDERR.

"""


__author__ = 'Laurent A.V. Szyster <contact@laurentszyster.be>'


import exceptions


def encode (strings):
	"encode an sequence of 8-bit byte strings as netstrings"
	return ''.join (['%d:%s,' % (len (s), s) for s in strings])


def decode (buffer):
	"decode the netstrings found in the buffer, trunk garbage"
	size = len (buffer)
	prev = 0
	while prev < size:
		pos = buffer.find (':', prev)
		if pos < 1:
			break
			
		try:
			next = pos + int (buffer[prev:pos]) + 1
		except:
			break
	
		if next >= size:
			break
		
		if buffer[next] == ',':
			yield buffer[pos+1:next]

		else:
			break
			
		prev = next + 1


def netstrings (buffer):
	"decode the netstrings found in the buffer and return a list"
	return list (decode (buffer)) or [buffer]


def outline (encoded, format, indent):
	"Recursively format nested netstrings as a CRLF outline"
	n = tuple (decode (encoded))
	if len (n) > 0:
		return ''.join ([outline (
			e, indent + format, indent
			) for e in n])
			
	return format % encoded


def netlines (encoded, format='%s\n', indent='  '):
	"Beautify a netstring as an outline ready to log"
	n = tuple (decode (encoded))
	if len (n) > 0:
		return ''.join ([outline (
			e, format, indent
			) for e in n]) + '\n'
			
	return format % encoded


class NetstringsError (exceptions.Exception): pass


def netpipe (more, BUFFER_MAX=0):
	"""A practical netstrings pipe generator
	
	Decode the stream of netstrings produced by more (), raise 
	a NetstringsError exception on protocol failure or StopIteration
	when the producer is exhausted.
	
	If specified, the BUFFER_MAX size must be more than twice as
	big as the largest netstring piped through (although netstrings
	strictly smaller than BUFFER_MAX may pass through without raising
	an exception).
	"""
	buffer = more ()
	while buffer:
		pos = buffer.find (':')
		if pos < 0:
			raise NetstringsError, '1 not a netstring' 
		try:
			next = pos + int (buffer[:pos]) + 1
		except:
			raise NetstringsError, '2 not a valid length'
	
		if 0 < BUFFER_MAX < next:
			raise (
				NetstringsError, 
				'3 buffer overflow (%d bytes)' % BUFFER_MAX
				)
			
		while next >= len (buffer):
			data = more ()
			if data:
				buffer += data
			else:
				raise NetstringsError, '4 end of pipe'
		
		if buffer[next] == ',':
			yield buffer[pos+1:next]

		else:
			raise NetstringsError, '5 missing coma'

		buffer = buffer[next+1:]
		if buffer == '' or buffer.isdigit ():
			buffer += more ()

	#
	# Note also that the first call to more must return at least the
	# encoded length of the first netstring, which practically is (or
	# should be) allways the case (for instance, piping in a netstring
	# sequence from a file will be done by blocks of pages, typically
	# between 512 and 4096 bytes, maybe more certainly not less).


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
		command = 'outline'
 	if command in ('outline', 'decode'):
 		if len (sys.argv) > 2:
	 		if len (sys.argv) > 3:
	 			try:
	 				buffer_max = int (sys.argv[3])
				except:
					sys.stderr.write (
						'3 invalid buffer max\n'
						)
					sys.exit (3)
					
			else:
				buffer_max = 0
 			try:
 				buffer_more = int (sys.argv[2])
			except:
				sys.stderr.write ('2 invalid buffer size\n')
				sys.exit (2)
				
		else:
	 		buffer_more = 4096
		def more ():
			return sys.stdin.read (buffer_more)
		if command == 'outline':
			for n in netpipe (more, buffer_max):
				sys.stdout.write (netlines (n))
		else:
			for n in netpipe (more, buffer_max):
				pass
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
