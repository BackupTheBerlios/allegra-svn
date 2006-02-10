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

class Finalization (object):

        finalization = None
        
        async_finalized = async_loop.async_finalized

        def __del__ (self):
                if self.finalization != None:
                         self.async_finalized.append (self)


# Branch

class Finalizations (Finalization):

	def __init__ (self, finalizations):
		self.finalizations = finalizations

	def __call__ (self, finalized):
		for finalization in self.finalizations:
			finalization (finalized)

def branch (branched, finalization):
	try:
		branched.finalization.finalizations.append (finalization)
	except:
		branched.finalization = Finalizations ([
			branched.finalization, finalization
			])
		
		
# Continue

class Continuation (object):

        finalization = None
        async_finalized = async_loop.async_finalized
        
        def __call__ (self): pass

        def __del__ (self):
                if self.finalization != None:
                         self.async_finalized.append (self)

	
def continuation (finalizations):
	"combines continuations into one execution path"
        i = iter (finalizations)
	first = continued = i.next ()
        try:
        	while True:
                        continued.finalization = i.next ()
                        continued = continued.finalization
        except StopIteration:
                pass
	return first, continued


class Continue (Continuation):
        
	def __init__ (self, finalizations):
		self.__call__, self.continued = continuation (
                        finalizations
                        )

# Join
#
# the equivalent of "thread joining" with finalization does not really need 
# a specific interface because it is enough to set the "joining" finalized
# as the finalization of all "joined" finalized.
#
#        joined.finalization = joining
#
# how simple ...

def join (finalizations, continuation):
        def finalize (finalized):
                for joined in finalizations:
                        joined.finalization = continuation
        return finalize
                

class Join (Continuation):

        def __init__ (self, finalizations):
                self.finalizations = finalizations
        
        def __call__ (self, finalized):
                if self.finalizations:
                        # start
                        for joined in self.finalizations:
                                joined.finalization = self
                        self.finalizations = None
                #
                # join

# Why does is it a good idea to use finalizations for continuation?
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