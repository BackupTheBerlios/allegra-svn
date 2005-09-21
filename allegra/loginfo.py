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

import sys

def compact_traceback ():
	# taken from asyncore, moved out serialization 
	#
        t, v, tb = sys.exc_info ()
        tbinfo = []
        # assert tb # Must have a traceback
        while tb:
                tbinfo.append ((
                        tb.tb_frame.f_code.co_filename,
                        tb.tb_frame.f_code.co_name,
                        str (tb.tb_lineno)
                        ))
                tb = tb.tb_next
        # just to be safe
        del tb
        return t, v, tbinfo


# The default logger implementation, logs uncategorized entries like
#
#	log ('output')
#
# to STDOUT and categorized entries with no handlers, like:
#
#	log ('404 Not found', 'HTTP Error')
#
# to STDERR. It does what the simplest program requires, and comes
# with a Write_and_flush wrapper for buffered files (you don't want your
# logs to be buffered!).

class Write_and_flush:
	
	def __init__ (self, file):
		self.file = file

	def __call__ (self, data):
		self.file.write (data)
		self.file.flush ()

		
def write_and_flush (file):
	if hasattr (file, 'flush'):
		return Write_and_flush (file)
		
	return file


class Loginfo_stdio:

	def __init__ (self, stdout=None, stderr=None):
		self.loginfo_stdout = write_and_flush (stdout or sys.stdout)
		self.loginfo_stderr = write_and_flush (stderr or sys.stderr)
		self.loginfo_loggers = {None: self}

	def __call__ (self, data):
		self.loginfo_stdout (data)

	def log (self, data, info=None):
		if self.loginfo_loggers.has_key (info):
			self.loginfo_loggers[info] (data + '\n')
		else:
			self.loginfo_stderr ('%s%s\n' % (info, data))

	def loginfo_stdio (self, stdout, stderr):
		prev = (self.loginfo_stdout, self.loginfo_stderr)
		(self.loginfo_stdout, self.loginfo_stderr) = (stdout, stderr)
		return prev
	
	
def loginfo_stdio_detach (stdout, stderr):
	sys.stdin.close ()
	sys.stdout.close ()
	sys.stderr.close ()
	Loginfo.loginfo_logger = Loginfo_stdio (stdout, stderr)


# The Loginfo class implementation

class Loginfo:

        loginfo_logger = None # can be overriden by instances or by classes

	def loginfo_log (self, data, info=None):
                """log the message with an optional category, prefixed
                with the instance __repr__
                """
		if Loginfo.loginfo_logger == None:
			Loginfo.loginfo_logger = Loginfo_stdio ()
		self.loginfo_logger.log ('%r%s' % (self, data), info)

	log = loginfo_log

	def loginfo_null (self, data, info=None):
                'drop the message to log'
                pass

	def loginfo_toggle (self):
		'toggle loginfo on/off for this instance'
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

	def loginfo_traceback (self):
		'logs as <traceback /> and return a compact traceback list'
		# makes sure to log the traceback even when loginfo is "off"
		cbt = compact_traceback ()
		self.loginfo_log (
			'<![CDATA[%s:%s%s]]!>' % (
				cbt[0], cbt[1], ''.join ([
					' [%s|%s|%s]' % x for x in cbt[2]
					])
				),
			'<traceback />'
			)
		return cbt

	def __repr__ (self):
		return '<%s pid="%x"/>' % (
			self.__class__.__name__, id (self)
			)


# The Loginfo module implementation

def loginfo_toggle (Class=Loginfo):
	'toggle loginfo on/off for this Class'
	if Class.log == Loginfo.loginfo_null:
		Class.log = Class.loginfo_log
		return 1
	
	else:
		Class.log = Class.loginfo_null
		return 0


def loginfo_log (data, info=None):
	if Loginfo.loginfo_logger == None:
		Loginfo.loginfo_logger = Loginfo_stdio ()
	Loginfo.loginfo_logger.log (data, info)

log = loginfo_log
	
def loginfo_null (data, info=None): pass


def loginfo_traceback ():
	ctb = compact_traceback ()
	loginfo_log (
		'<![CDATA[%s:%s %s]]!>' % (
			ctb[0], ctb[1], ''.join ([
				'[%s|%s|%s]' % x for x in ctb[2]
				])
			),
		'<traceback />'
		)
	return ctb
	
	
# Note about this implementation
#
# No care about encoding is taken here. This is an 8bit clean strings
# implementation. It will raise exceptions when passed unicode objects
# that cannot be encoded with the default encoding.
#
# If you need to log unicode strings, encode them first, preferrably as
# UTF-8. It makes no sense to implement encoding with Loginfo interfaces
# simply because one may require to log XML and therefore prefer to use
# ASCII and XML character references, while another logs text to a cp1252
# console (you know which one!).