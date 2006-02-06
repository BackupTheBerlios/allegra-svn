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


class Finalization (object):

	finalization = None

	def __del__ (self):
                if self.finalization != None:
                         async_loop.async_finalized.append (self)

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


class Continue (object):

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
#
# Why does is it a good idea to use the GC for continuation?
#
# Practically, this "hack" ensures that any program using continuation
# for its flow is then "memory-driven", naturally "memory-safe" because 
# it runs as memory is released, mecanically allocating memory for a new
# task only if it released the memory allocated for the previous one.
# So, any further memory use is defered *after* having made room for it. 
#
# This is a very interesting property for a mission critical program, which
# makes Allegra's web peer a very interesting pateform for some business 
# network applications development.
# 
# The practical use of finalizations in Allegra is to articulate PNS/TCP,
# program MIME workflows but also to attach a continuations to HTTP server
# requests. In this case, the finalization itself will not happen until the
# HTTP request instance is deleted. If you consider such finalization like 
# sending a mail asynchronously or logging synchronously to a BSDDB, freeing 
# up as much memory as possible before looks like a very good idea. The
# practical benefit of finalizations is that they help to conserve memory
# also by forcing programmers to remove all circular references in order 
# to run their programs to closure. And not leaking is a primary requirement
# for any long-running application like a PNS metabase or a web server.