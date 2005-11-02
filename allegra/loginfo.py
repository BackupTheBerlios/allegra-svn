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

import sys, types

from allegra import netstring, prompt


class Write_and_flush:
	
	"Wrapper class for buffered files that allways flush."
	
	def __init__ (self, file):
		self.file = file

	def __call__ (self, data):
		self.file.write (data)
		self.file.flush ()
		

def write_and_flush (file):
	"maybe wraps a file's write method with a Write_and_flush instance"
	if hasattr (file, 'flush'):
		return Write_and_flush (file)
		
	return file.write


class Loginfo_stdio:

	"Loginfo's log dispatcher implementation"
	
	def __init__ (self, stdout=None, stderr=None):
		self.loginfo_stdout = write_and_flush (stdout or sys.stdout)
		self.loginfo_stderr = write_and_flush (stderr or sys.stderr)
		self.loginfo_loggers = {}

	def loginfo_stdio (self, stdout, stderr):
		"set new STDOUT and STDERR, backup the previous ones"
		prev = (self.loginfo_stdout, self.loginfo_stderr)
		(self.loginfo_stdout, self.loginfo_stderr) = (stdout, stderr)
		return prev

	def loginfo_log (self, data, info=None):
		"log netstrings to STDOUT, a category handler or STDERR"
		if info == None:
			self.loginfo_stdout ('%d:%s,' % (len (data), data))
		elif self.loginfo_loggers.has_key (info):
			self.loginfo_loggers[info] (
				'%d:%s,' % (len (data), data)
				)
		else:
			encoded = netstring.netstrings_encode ((info, data))
			self.loginfo_stderr (
				'%d:%s,' % (len (encoded), encoded)
				)

	def loginfo_debug (self, data, info=None):
		"log netlines to STDOUT, a category handler or STDERR"
		assert type (data) == types.StringType
		if info == None:
			self.loginfo_stdout (netstring.netlines (data))
		elif self.loginfo_loggers.has_key (info):
			self.loginfo_loggers[info] (
				netstring.netlines (data)
				)
		else:
			assert type (info) == types.StringType
			encoded = netstring.netstrings_encode ((
				info, data
				))
			self.loginfo_stderr (
				netstring.netlines (encoded)
				)

	if __debug__:
		log = loginfo_debug
	else:
		log = loginfo_log


def compact_traceback_netstrings (ctb):
	"encode a compact traceback tuple as netstrings"
 	return netstring.netstrings_encode ((
 		'%s' % ctb[0], '%s' % ctb[1], 
 		netstring.netstrings_encode (['|'.join (x) for x in ctb[2]])
 		))


class Loginfo:

	loginfo_logger = Loginfo_stdio ()
	
	def __repr__ (self):
		return '<%s pid="%x"/>' % (
			self.__class__.__name__, id (self)
			)

	def loginfo_log (self, data, info=None):
		"""log a message with this instance's __repr__ and an 
		optional category"""
		self.loginfo_logger.log (netstring.netstrings_encode ((
			'%r' % self, '%s' % data
			)), info)

	log = loginfo_log

	def loginfo_null (self, data, info=None):
                "drop the message to log"
                pass
                
        def loginfo_logging (self):
        	"return True if the instance is logging"
        	return self.log != self.loginfo_null

	def loginfo_toggle (self, logging=None):
		"toggle logging on/off for this instance"
		if logging == None:
			if self.log == self.loginfo_null:
				try:
					del self.log
				except:
					self.log = self.loginfo_log
			else:
				try:
					del self.log
				except:
					self.log = self.loginfo_null
			return self.log != self.loginfo_null
			
		if logging == True and self.log == self.loginfo_null:
			self.log = self.loginfo_log
		elif logging == False and self.log == self.loginfo_log:
			self.log = self.loginfo_null
		return logging

	def loginfo_traceback (self):
		"""return a compact traceback tuple and log it encoded as 
		netstrings, along with this instance's __repr__, in the
		'traceback' category"""
		ctb = prompt.compact_traceback ()
		self.loginfo_log (
			compact_traceback_netstrings (ctb), 'traceback'
			)
		return ctb


def log (data, info=None):
	"log a message with an optional category"
	Loginfo.loginfo_logger.log (data, info)

def loginfo_toggle (logging=None, Class=Loginfo):
	"toggle logging on/off for the Class specified or Loginfo"
	if logging == None:
		if Class.log == Class.loginfo_null:
			Class.log = Class.loginfo_log
			return True
			
		Class.log = Class.loginfo_null
		return False
		
	if logging == True and Class.log == Class.loginfo_null:
		Class.log = Class.loginfo_log
	elif logging == False and Class.log == Class.loginfo_log:
		Class.log = Class.loginfo_null
	return logging
	
def loginfo_traceback ():
	"return a traceback and log it in the 'traceback' category"
	ctb = prompt.compact_traceback ()
	Loginfo.loginfo_logger.log (
		compact_traceback_netstrings (ctb), 'traceback'
		)
	return ctb


assert None == log ('loginfo', 'debug')


# DESCRIPTION
#
# The Loginfo interface and implementation provide a simpler, yet more
# powerfull and practical logging facility than the one currently integrated
# with Python.
#
# First is uses netstrings instead of CR or CRLF delimeted lines for I/O
# encoding, solving ahead many problems of the log consumers. Second it
# is well adapted to a practical development cycle and by defaults implement
# a simple scheme that suites well a shell pipe like:
#
#	pipe < input 1> output 2> errors
#
#
# Last but not least, the loginfo_log is compatible with asyncore logging 
# interfaces (which is no wonder, it is inspired from Medusa's original
# logging facility module).
#
# EXAMPLE
#
# 	>>> from allegra import loginfo
#	18:
#	  5:debug,
#	  7:loginfo,
#	,
#
#	>>> loginfo.log ('data')
#	4:data,
#	>>> loginfo.log ('data', 'info')
#	14:
#	  4:info,
#	  4:data,
#	,
#	>>> try:
#		foobar ()
#	except:
#		ctb = loginfo.loginfo_traceback ()
#	91:
#	  9:traceback,
#	  75:
#	    20:exceptions.NameError,
#	    28:name 'foobar' is not defined,
#	    15:11:<stdin>|?|2,,
#	  ,
#	,
#
#	>>> logged = loginfo.Loginfo ()
#	>>> logged.log ('data')
#	34:
#	  23:<Loginfo pid="8da4e0"/>,
#	  4:data,
#	,
#	>>> logged.log ('data', 'info')
#	45:
#	  4:info,
#	  34:
#	    23:<Loginfo pid="8da4e0"/>,
#	    4:data,
#	  ,
#	,
