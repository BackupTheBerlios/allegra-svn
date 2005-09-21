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

"Standard Synchronous I/O, with a line prompt and a Python prompt."

import sys

from allegra.loginfo import Loginfo, Loginfo_stdio
from allegra import async_loop
from allegra.thread_loop import Thread_loop


class Sync_stdio_file:

	def __init__ (self, file, async_write):
		self.write = async_write
		

class Sync_stdio (Thread_loop):

	def __init__ (self):
		# create a loginfo_logger if one has not been instanciated yet, the
		# substitute loginfo's stdout and stderr methods as well as the
		# sys.stdout and sys.stderr files
		#
		if Loginfo.loginfo_logger == None:
			Loginfo.loginfo_logger = Loginfo_stdio ()
		(
			self.sync_stdout, self.sync_stderr
			) = Loginfo.loginfo_logger.loginfo_stdio (
				self.async_stdout, self.async_stderr
				)
		self.sys_stdout, self.sys_stderr = sys.stdout, sys.stderr
		sys.stdout, sys.stderr = (
			Sync_stdio_file (sys.stdout, self.async_stdout),
			Sync_stdio_file (sys.stderr, self.async_stderr)
			)
		Thread_loop.__init__ (self)

	def __repr__ (self):
		return '<sync-stdio queued="%d"/>' % len (self.thread_loop_queue)

	def async_stdout (self, data):
		self.thread_loop_queue.push (
			lambda o=self.sync_stdout, d=data: o (d)
			)

	def async_stderr (self, data):
		self.thread_loop_queue.push (
			lambda e=self.sync_stderr, d=data: e (d)
			)

	def async_stdio_stop (self):
		sys.stdout, sys.stderr = self.sys_stdout, self.sys_stderr
		self.loginfo_logger.loginfo_stdio (
			self.sync_stdout, self.sync_stderr
			)
		self.thread_loop_stop ()


class Sync_stdoe (Sync_stdio):

	def thread_loop_init (self):
		self.thread_loop_queue.push (self.sync_stdin)
		return Thread_loop.thread_loop_init (self)

	def sync_stdin (self):
		sys.stdin.close ()
		assert None == self.log ('<stdin-close/>', '')


class Sync_prompt (Sync_stdio):

	sync_prompt_ready = 0

	def __init__ (self):
		self.async_catch = async_loop.async_catch
		async_loop.async_catch = self.sync_prompt_catch
		Sync_stdio.__init__ (self)
		
	def sync_prompt_catch (self):
		if self.sync_prompt_ready:
			self.thread_loop_queue.push (
				lambda
				s=self.sync_stderr, d='[CTRL+C]\n':
				s (d)	
				)
		else:
			self.thread_loop_queue.push (self.sync_stdin)
			self.sync_prompt_ready = 1
		return 1

	def sync_prompt (self):
		self.sync_prompt_ready = 0

	def sync_stdin (self):
		self.sync_stderr ('>>> ')
		line = sys.stdin.readline ()[:-1]
		if line == '':
			self.select_trigger (self.sync_prompt)
			return

		self.sync_readline (line)
		self.thread_loop_queue.push (self.sync_stdin)
		
	def sync_readline (self, line):
		self.select_trigger.log ('<![CDATA[%s]]!>' % line)

	def async_stdio_stop (self):
		async_loop.async_catch = self.async_catch
		Sync_stdio.async_stdio_stop (self)


class Python_prompt (Sync_prompt):

	def __init__ (self, env=None):
		self.python_prompt_env = env or {'self': self}
		Sync_prompt.__init__ (self)

	def sync_readline (self, line):
		try:
			# try eval first.  If that fails, try exec.  If that fails, hurl.
			try:
				co = compile (line, repr (self), 'eval')
				self.select_trigger (
					lambda e=self.async_python_eval, l=co: e (l)
					)
			except SyntaxError:
				co = compile (line, repr (self), 'exec')
				self.select_trigger (
					lambda e=self.async_python_exec, l=co: e (l)
					)
		except:
			self.loginfo_traceback ()

	def async_python_eval (self, co):
		try:
			data = eval (co, self.python_prompt_env)
			if data != None:
				data = data.__repr__()
		except:
			self.select_trigger.loginfo_traceback ()
		else:
			if data:
				self.async_stderr (data + '\n')

	def async_python_exec (self, co):
		try:
			exec co in self.python_prompt_env
		except:
			self.select_trigger.loginfo_traceback ()

	def async_stdio_stop (self):
		del self.python_prompt_env # break circular reference
		Sync_prompt.async_stdio_stop (self)
		

if __name__ == '__main__':
	if '-d' in sys.argv:
		sys.argv.remove ('-d')
		Python_prompt ().start ()
	else:
		import time
		stdio = Sync_stdoe ()
		async_loop.async_defer (
			time.time () + 10,
			lambda when, s=stdio: s.async_stdio_stop
			)
		stdio.start ()
		del stdio
	try:
		async_loop.loop ()
	except:
		async_loop.loginfo.loginfo_traceback ()
