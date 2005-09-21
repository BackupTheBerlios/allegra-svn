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

"a Finalization implementation for async_loop's asynchronous network peers"

from allegra import async_loop


# Finalize

class Finalization:

	finalization = None

	def finalization_finalize (self):
		# if any, thunk the finalization through the async_finalized
		# loop and let async_loop.async_immediate call it ...
		if self.finalization == None:
			return

		async_loop.async_finalized.append (
			lambda f=self.finalization, o=self: f (o)
			)
		self.finalization = None
		#
		# since exceptions are ignored in __del__ and result in
		# warnings instead, the same applies to the 'finalization'
		# callable and they should not be more complex than defering
		# for immediate execution in async_loop.

	__del__ = finalization_finalize
	
	# the purpose of finalization is to implement asynchronous pipe-like
	# interfaces, like this:
	#
	#	get (
	#		'http://del.icio.us/tag/semantic'
	#		).finalization = mailto (
	#			'contact@laurentszyster.be'
	#			)
	#
	# when the instance returned by wget is dereferenced by its pipeline
	# HTTP factory, it will be passed as argument to the callable instance
	# factoried by 'mailto'. Effectively, the collected web page is mailed
	# as an attachement to me.
	#
	# there is no other practical way to program asynchronous peer
	# workflow from the interpreter's prompt. 
	#
	# this is the REBOL way ... with a *real* language ;-)


# Join
#
# the equivalent of "thread joining" with finalization does not need a 
# specific interface because it is enough to set the "joining" finalized
# as the finalization of all "joined" finalized.
#
#	joined.finalization = joining
#
# how simple ...


# Branch

class Finalizations (Finalization):

	def __init__ (self, finalizations):
		self.finalizations = finalizations

	def __call__ (self, instance):
		for finalization in self.finalizations:
			finalization (instance)

def finalization_extend (extended, finalization):
	try:
		extended.finalization.finalizations.append (finalization)
	except:
		extended.finalization = Finalizations ([
			extended.finalization, finalization
			])
		
		
# Continue
	
def continuation (finalizations):
	"combines finalization instances into one execution path"
	assert len (finalizations) > 1
	last = finalization = finalizations.pop ()
	while finalizations:
		finalizations[-1].finalization = finalization
		finalization = finalizations.pop ()
	return finalization, last


class Continue:

	finalization = None

	def __init__ (self, finalizations):
		self.__call__, self.last = continuation (finalizations)

	def __del__ (self):
		self.last.finalization = self.finalization


# This is my own "cheap" pure Python 2.2 implementation of PEP-0342
#
# Finalization is a Lisp construct, and finally somebody else noticed that
# the GIL and cyclic garbage collector could be applied to good asynchronous
# use ...