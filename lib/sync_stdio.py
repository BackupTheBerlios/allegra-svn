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

"""Synchronous Standard I/O interfaces, with a Python prompt implementation.

SYNOPSIS

the development console, with full all debug assertion logs, 
outlined for readability and CRLF applications (grep, more, tail, etc ...):

        python sync_stdio.py

or a quiet outlined console:

	python -OO sync_stdio.py -d

or netstring logs for tests scripts:

        python -OO sync_stdio.py < script.py 1> stdout 2> stderr

"""

import sys

from allegra import prompt, loginfo, async_loop, finalization, thread_loop


class Sync_stdio_file:

	def __init__ (self, async_write):
		self.write = async_write
		
	def writelines (self, lines):
		for line in lines:
			self.write (line)
			

class Sync_stdio (thread_loop.Thread_loop):

	def __init__ (self):
                self.async_loop_catch = async_loop.async_catch
                async_loop.async_catch = self.async_prompt_catch
		stdout, stderr = (
			Sync_stdio_file (self.async_stdout),
			Sync_stdio_file (self.async_stderr)
			)
		(
			self.sync_stdout, self.sync_stderr
			) = loginfo.Loginfo.loginfo_logger.loginfo_stdio (
				stdout, stderr
				)
		self.sys_stdout, self.sys_stderr = sys.stdout, sys.stderr
		sys.__stdout__, sys.__stderr__ = stdout, stderr
		thread_loop.Thread_loop.__init__ (self)

	def __repr__ (self):
		return 'sync-stdio'

	def async_stdout (self, data):
		self.thread_loop_queue ((self.sync_stdout, (data,)))

	def async_stderr (self, data):
		self.thread_loop_queue ((self.sync_stderr, (data,)))

	def async_stdio_stop (self):
                async_loop.async_catch = self.async_loop_catch
                self.async_loop_catch = None
		sys.__stdout__, sys.__stderr__ = (
			self.sys_stdout, self.sys_stderr
			)
		del self.sys_stdout, self.sys_stderr
                del self.sync_stdout, self.sync_stderr
		try:
			del self.log
		except:
			pass
		loginfo.Loginfo.loginfo_logger.loginfo_stdio (
			loginfo.write_and_flush (sys.stderr), 
			loginfo.write_and_flush (sys.stdout)
			)
		self.thread_loop_queue (None)
                return True

        async_prompt_catch = async_stdio_stop


class Sync_stdoe (Sync_stdio):

	def __repr__ (self):
		return 'sync-stdoe'

	def thread_loop_init (self):
                self.select_trigger_log (
                        'Press CTRL+C to stop synchronous I/O', 'info'
                        )
		self.thread_loop_queue ((self.sync_stdin, ()))
		return True

	def sync_stdin (self):
		sys.stdin.close ()
		assert None == self.select_trigger_log (
			'stdin_close', 'debug'
			)


class Sync_prompt (Sync_stdio):

	sync_prompt_ready = not __debug__

	def thread_loop_init (self):
                if self.sync_prompt_ready:
                        self.thread_loop_queue ((self.sync_stdin, ()))
                else:
                        self.select_trigger_log (
                                'press CTRL+C to open and close the console', 
                                'info'
                                )
		return True
		
	def async_prompt_catch (self):
		if self.sync_prompt_ready:
			self.thread_loop_queue ((
				self.sync_stderr, ('[CTRL+C]\n',)
				))
		else:
			self.thread_loop_queue ((self.sync_stdin, ()))
			self.sync_prompt_ready = True
		return True

	def sync_stdin (self):
		self.sync_stderr ('>>> ')
		line = sys.stdin.readline ()[:-1]
		if line == '':
			self.select_trigger ((self.async_prompt, ()))
			return

		self.select_trigger ((self.async_readline, (line,)))
		
        def async_prompt (self):
                self.sync_prompt_ready = False
                
	def async_readline (self, line):
		assert None == self.log (line)
		self.thread_loop_queue ((self.sync_stdin, ()))


class Python_prompt (Sync_prompt):

	def __init__ (self, env=None):
		self.python_prompt_env = env or {'prompt': self}
		Sync_prompt.__init__ (self)

	def __repr__ (self):
		return 'python-prompt'

	def async_readline (self, line):
		method, result = prompt.python_prompt (
			line, self.python_prompt_env
			)
		if method == 'excp':
			self.loginfo_traceback (result)
		elif result != None:
			self.async_stderr ('%r\n' % (result,))
		self.thread_loop_queue ((self.sync_stdin, ()))

	def async_stdio_stop (self):
		self.python_prompt_env = None # break circular reference
		return Sync_prompt.async_stdio_stop (self)
		

if __name__ == '__main__':
        import sys
        if '-d' in sys.argv:
                sys.argv.remove ('-d')
                loginfo.Loginfo_stdio.log = \
                        loginfo.Loginfo_stdio.loginfo_netlines     
	assert None == loginfo.log (
		'Allegra Prompt'
		' - Copyright 2005 Laurent A.V. Szyster'
		' | Copyleft GPL 2.0', 'info'
		)
        Python_prompt ().start ()
        async_loop.dispatch ()
        assert None == finalization.collect ()