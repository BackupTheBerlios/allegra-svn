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

from allegra.fifo import FIFO_big, FIFO_pipeline

class Pipeline:

	pipeline_keep_alive = 0
	pipeline_sleeping = 0

	def __init__ (self, requests=None, responses=None):
		self.pipeline_requests_fifo = requests or FIFO_big ()
		self.pipeline_responses_fifo = responses or FIFO_big ()

	def pipeline_push (self, request):
		self.pipeline_requests_fifo.push (request)
		if self.pipeline_sleeping:
			self.pipeline_sleeping = 0
			self.pipeline_wake_up ()

	def pipeline_wake_up ():
		pass # to subclass with your pipeline action
	
	def pipeline_merge (self):
		if self.pipeline_requests_fifo.is_empty ():
			if self.pipeline_responses_fifo.is_empty ():
				return None
			
			else:
				return self.pipeline_responses_fifo
			
		else:
			if self.pipeline_responses_fifo.is_empty ():
				return self.pipeline_requests_fifo
			
			else:
				fifo = FIFO_pipeline ()
				fifo.push_fifo (self.pipeline_responses_fifo)
				fifo.push_fifo (self.pipeline_requests_fifo)
				return fifo
