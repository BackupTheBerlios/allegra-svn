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

"Synchronous Standard I/O interfaces, with a Python prompt implementation."

import sys

from allegra import loginfo, async_loop, thread_loop


#class Sync_stdio_file:
#
#	def __init__ (self, async_write):
#		self.write = async_write
		

class Sync_stdio (thread_loop.Thread_loop):

	def __init__ (self):
		(
			self.sync_stdout, self.sync_stderr
			) = loginfo.Loginfo.loginfo_logger.loginfo_stdio (
				self.async_stdout, self.async_stderr
				)
		#self.sys_stdout, self.sys_stderr = sys.stdout, sys.stderr
		#sys.stdout, sys.stderr = (
		#	Sync_stdio_file (self.async_stdout),
		#	Sync_stdio_file (self.async_stderr)
		#	)
		thread_loop.Thread_loop.__init__ (self)

	def __repr__ (self):
		return '<sync-stdio id="%x"/>' % id (self)

	def async_stdout (self, data):
		self.thread_loop_queue ((self.sync_stdout, (data,)))

	def async_stderr (self, data):
		self.thread_loop_queue ((self.sync_stderr, (data,)))

	def async_stdio_stop (self):
		# sys.stdout, sys.stderr = self.sys_stdout, self.sys_stderr
		try:
			del self.log
		except:
			pass
		loginfo.Loginfo.loginfo_logger.loginfo_stdio (
			self.sync_stdout, self.sync_stderr
			)
		self.thread_loop_stop ()


class Sync_stdoe (Sync_stdio):

	def thread_loop_init (self):
		self.thread_loop_queue ((self.sync_stdin, ()))
		return True

	def sync_stdin (self):
		sys.stdin.close ()
		assert None == self.select_trigger_log (
			'stdin_close', 'debug'
			)


class Sync_prompt (Sync_stdio):

	sync_prompt_ready = False

	def __init__ (self):
		self.async_catch = async_loop.async_catch
		async_loop.async_catch = self.sync_prompt_catch
		Sync_stdio.__init__ (self)
		
	def sync_prompt (self):
		self.sync_prompt_ready = False
		
	def sync_prompt_catch (self):
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
			self.select_trigger ((self.sync_prompt, ()))
			return

		self.sync_readline (line)
		self.thread_loop_queue ((self.sync_stdin, ()))
		
	def sync_readline (self, line):
		assert None == self.select_trigger_log (line)

	def async_stdio_stop (self):
		async_loop.async_catch = self.async_catch
		Sync_stdio.async_stdio_stop (self)


class Python_prompt (Sync_prompt):

	def __init__ (self, env=None):
		self.python_prompt_env = env or {'self': self}
		Sync_prompt.__init__ (self)

	def sync_readline (self, line):
		try:
			# try eval first.
			try:
				co = compile (line, repr (self), 'eval')
				self.select_trigger ((
					self.async_python_eval, (co,)
					))
			except SyntaxError:
				# If that fails, try exec.  
				co = compile (line, repr (self), 'exec')
				self.select_trigger ((
					self.async_python_exec, (co,)
					))
		except:
			# If that fails, hurl ...
			self.select_trigger_traceback ()

	def async_python_eval (self, co):
		try:
			data = eval (co, self.python_prompt_env)
			if data != None:
				data = data.__repr__()
		except:
			self.loginfo_traceback ()
		else:
			if data:
				self.async_stderr (data + '\n')

	def async_python_exec (self, co):
		try:
			exec co in self.python_prompt_env
		except:
			self.loginfo_traceback ()

	def async_stdio_stop (self):
		del self.python_prompt_env # break circular reference
		Sync_prompt.async_stdio_stop (self)
		

if __name__ == '__main__':
	assert None == loginfo.log (
		'Allegra Prompt'
		' - Copyright 2005 Laurent A.V. Szyster'
		' | Copyleft GPL 2.0', 'info'
		)
	Python_prompt ().start ()
	async_loop.loop ()