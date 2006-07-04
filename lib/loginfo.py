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

"http://laurentszyster.be/blog/loginfo/"

import sys, types

from allegra import netstring, prompt


class Write_and_flush (object):
	
	"Wrapper class for buffered files that allways flush."
	
	def __init__ (self, file):
		self.file = file

	def __call__ (self, data):
		self.file.write (data)
		self.file.flush ()
		

def write_and_flush (instance):
	"""return a callable: maybe wraps a file's write method with a 
	Write_and_flush instance; a non-buffered file write method; or
	the instance itself otherwise"""
	if hasattr (instance, 'flush'):
		return Write_and_flush (instance)
		
	if hasattr (instance, 'write'):
		return instance.write
		
	return instance


class Loginfo_stdio (object):

	"Loginfo's log dispatcher implementation"
	
	loginfo_stdout = loginfo_stderr = None
	
	def __init__ (self, stdout=None, stderr=None):
		self.loginfo_stdio (
			stdout or sys.stdout, stderr or sys.stderr
			)
		self.loginfo_loggers = {}

	def loginfo_stdio (self, stdout, stderr):
		"set new STDOUT and STDERR, backup the previous ones"
		prev = (self.loginfo_stdout, self.loginfo_stderr)
		self.loginfo_stdout = write_and_flush (stdout)
		self.loginfo_stderr = write_and_flush (stderr)
		return prev

	def loginfo_netstrings (self, data, info=None):
		"log netstrings to STDOUT, a category handler or STDERR"
		if info == None:
			self.loginfo_stdout ('%d:%s,' % (len (data), data))
		elif self.loginfo_loggers.has_key (info):
			self.loginfo_loggers[info] (
				'%d:%s,' % (len (data), data)
				)
		else:
			encoded = netstring.encode ((info, data))
			self.loginfo_stderr (
				'%d:%s,' % (len (encoded), encoded)
				)

	def loginfo_netlines (self, data, info=None):
		"log netoutlines to STDOUT, a category handler or STDERR"
		assert type (data) == types.StringType
		if info == None:
			self.loginfo_stdout (
				netstring.netlines (data)
				)
		elif self.loginfo_loggers.has_key (info):
			self.loginfo_loggers[info] (
				netstring.netlines (data)
				)
		else:
			assert type (info) == types.StringType
			self.loginfo_stderr (netstring.netlines (
				netstring.encode ((
					info, data
					))
				))

	if __debug__:
		log = loginfo_netlines
	else:
		log = loginfo_netstrings


def compact_traceback_netstrings (ctb):
	"encode a compact traceback tuple as netstrings"
 	return netstring.encode ((
 		ctb[0], ctb[1], 
 		netstring.encode ([' | '.join (x) for x in ctb[2]])
 		))


class Loginfo (object):

	loginfo_logger = Loginfo_stdio ()
	
	def __repr__ (self):
		return '%s id="%x"' % (
			self.__class__.__name__, id (self)
			)

	def loginfo_log (self, data, info=None):
		"""log a message with this instance's __repr__ and an 
		optional category"""
		self.loginfo_logger.log (netstring.encode ((
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

	def loginfo_traceback (self, ctb=None):
		"""return a compact traceback tuple and log it encoded as 
		netstrings, along with this instance's __repr__, in the
		'traceback' category"""
		if ctb == None:
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
	
def loginfo_traceback (ctb=None):
	"return a traceback and log it in the 'traceback' category"
	if ctb == None:
		ctb = prompt.compact_traceback ()
	Loginfo.loginfo_logger.log (
		compact_traceback_netstrings (ctb), 'traceback'
		)
	return ctb


__doc__ = "http://laurentszyster.be/blog/loginfo/"

__author__ = 'Laurent A.V. Szyster <contact@laurentszyster.be>'
        

# SYNOPSIS
#
# >>> from allegra import loginfo
#>>> loginfo.log ('message')
# message
# >>> loginfo.log ('message', 'info')
# info
# message
#	
# >>> try:
# ...    foobar ()
# ... except:
# ...    ctb = loginfo.loginfo_traceback ()
# traceback
#   exceptions.NameError
#   name 'foobar' is not defined
#     <stdin> | ? | 2
#
# >>> logged = loginfo.Loginfo ()
# >>> logged.log ('message')
# Loginfo id="8da4e0"
# message
#	
# >>> logged.log ('message', 'info')
# info
#   Loginfo id="8da4e0"
#   message
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
# However "slow" this Python facily is, it offers a next-best trade-off
# between performance in production and flexibility for both debugging and
# maintenance. All debug and information logging can be effectively disabled,
# either skipped in case of:
#
#	assert None == loginfo.log (...)
#
# or simply dropped, yielding not access to possibly blocking or buffering
# process handling the log output. The ability to filter out or filter in
# log at the instance or class level is enough to satisfy the most demanding
# application administrator (as for categories, there are none defined, do
# as it please you ;-).
#
# Last but not least, the loginfo_log is compatible with asyncore logging 
# interfaces (which is no wonder, it is inspired from Medusa's original
# logging facility module).
#
