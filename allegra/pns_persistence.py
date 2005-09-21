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

# TODO: rename this module to pns_resolution.py

from glob import glob
from bsddb import db

from cPickle import dumps, loads
#
# TODO: maybe replace cPickle by a faster dictionnary made of netstrings
#       and actually search for strings instead of instanciating hashes
#       ...
#

from allegra.thread_loop import Thread_loop
from allegra.netstring import netstrings_encode


class PNS_persistence (Thread_loop):

	pns_persistence = None

	def __init__ (self, pns_peer):
		self.pns_peer = pns_peer
		self.pns_root = self.pns_peer.pns_root
		Thread_loop.__init__ (self)
		self.start ()
		
	def __repr__ (self):
		return '<persistence/>'

	def thread_loop_init (self):
                try:
                        self.pns_persistence = db.DB ()
                        if glob (self.pns_root + '/statements.db'):
                        	self.pns_persistence.open (
                        		self.pns_root + '/statements.db'
                        		)
                  	else:
                        	self.pns_persistence.open (
                        		self.pns_root + '/statements.db',
                        		dbtype=db.DB_HASH,
                        		flags=db.DB_CREATE
                        		)
                except:
                        self.loginfo_traceback ()
                else:
                        assert None == self.log ('<open/>', '')
                        return 1

	def thread_loop_delete (self):
                if self.pns_persistence != None:
                        try:
                                self.pns_persistence.close ()
                        except:
                                self.loginfo_traceback ()
                        else:
                                del self.pns_persistence
                        	assert None == self.log ('<close/>', '')
                self.select_trigger (
                	self.pns_peer.pns_persistence_finalize
                	)
                del self.pns_peer
                
	# Resolution

	def pns_persistent (self, model):
		# store, retrieve and update, but also filter statements,
		# returns a tuple (persistent, stored), indicating wether
		# the statement is to be blocked and the object stored
		# previously if any.
		#
                sp = netstrings_encode (model[:2])
                stored = self.pns_persistence.get (sp)
                if stored == None:
                	# new (subject, predicate), store and pass
			self.pns_persistence [sp] = dumps (
				{model[3]: model[2]}
				)
			return True, None

		# load the {(object, context)} hash from the store
		persistents = loads (stored)
		o = persistents.get (model[3])
		if o == model[2]:
			# redundant contextual statement, block
			return False, None
			
		# dissent, update answer and pass
		if model[2] != '':
			persistents[model[3]] = model[2]
			self.pns_persistence[sp] = dumps (persistents)
		return True, o
		
        # PNS/TCP anonymous questions and named statements
                
	def pns_anonymous (self, model):
		# anonymous question, resolve all contexts.
                sp = netstrings_encode (model[:2])
                stored = self.pns_persistence.get (sp)
                if stored != None:
	          	bounce = model[:5]
	          	bounce[2] = netstrings_encode ([
				netstrings_encode (i) 
				for i in loads (stored).items ()
				])
			self.select_trigger (
				lambda p=self.pns_peer, m=bounce:
				p.pns_tcp_continue (m, '_')
				)
		self.select_trigger (
			lambda p=self.pns_peer, m=model:
			p.pns_tcp_continue (m, '.')
			)
		#
		# why not do anonymous answers too? well, the only use
		# for such syntax would be to find the context for a
		# given (subject,predicate,object) triple, which is
		# anyway provided by a more general (subject,predicate,)
		# question.
		
	def pns_statement (self, model):
		dissent, stored = self.pns_persistent (model)
		if dissent:
			if stored:
				# bounce any persistent statement stored
				# for the same subject, predicate and context
				# as this statement
				#
		          	bounce = model[:5]
		          	bounce[2] = stored
				self.select_trigger (
					lambda p=self.pns_peer, m=bounce:
					p.pns_tcp_continue (m, '_')
					)
			# let the peer continue this statement, try to relay
			# or route it to a subscribed context
			#
			self.select_trigger (
				lambda p=self.pns_peer, m=model:
				p.pns_statement_continue (m)
				)
		else:
			# redundant statement, echo request handling to the
			# user agent.
			#
			self.select_trigger (
				lambda p=self.pns_peer, m=model:
				p.pns_tcp_continue (m, '.')
				)

	# PNS/UDP circle

	def pns_pirp (self, name, addr):
		# bounce back a persistent protocol answer to the peer
		#
		encoded = '%d:%s,0:,' % (len (name), name)
		dissent, left = self.pns_persistent (
			(name, '', '', name)
			)
		if dissent and left:
			encoded += '%d:%s,' % (len (left), left)
		else:
			encoded += '0:,'
		self.select_trigger (
			lambda
			p=self.pns_peer, n=name, d=encoded, a=addr:
			p.pns_pirp_continue (n, d, a)
			)
		#
		# this is PIRP, restricted to PNS/UDP protocol questions.

	def pns_out_of_circle (self, name):
		# either join the last persistent right peer, or
		# route a protocol question
		#
		model = [name, '', '', name]
		dissent, left = self.pns_persistent (model)
		if left == None:
			self.select_trigger (
				lambda p=self.pns_peer, m=model:
				p.pns_semantic.pns_statement (m)
				)
			return
			
		self.select_trigger (
			lambda p=self.pns_peer, n=name, l=left:
			p.pns_join_continue (n, l)
			)

	def pns_question (self, model):
		# check persistence, bounce answer and route dissent
		dissent, stored = self.pns_persistent (model)
		if dissent:
			if stored:
				bounce = model[:]
				bounce[2] = stored
				self.select_trigger (
					lambda p=self.pns_peer, m=bounce:
					p.pns_statement_continue (m)
					)
			self.select_trigger (
				lambda p=self.pns_peer, m=model:
				p.pns_semantic.pns_statement (m)
				)
			
	def pns_answer (self, model):
		dissent, stored = self.pns_persistent (model)
		if dissent:
			self.select_trigger (
				lambda p=self.pns_peer, m=model:
				p.pns_semantic.pns_statement (m)
				)			
		
		
# Note about this implementation
#
# There is little other option than cPickle to store multiple contextual
# statements about the same subject and predicate in one single bsddb hash
# table. Other persistent datastructure, like multiple database tables (one
# per context) or another encoding of statements, are suboptimal, either too
# complex to implement or too slow.
#
# Managing one bsddb per context *is* problematic. Of course a database
# environnement and a thread may be cached for each subscribed contexts,
# but non-subscribed contexts will still require to be opened and closed
# for most requests and this would considerably impair performances if
# all contextual statements are to be retrieved at once. On the contrary,
# the one-big-table approach leverages bsddb's and system's caches/buffers.
#
# If the statements must be distributed between table, I suppose that one
# table per predicate would nicely do.
#
#
# No need for a "standard" format
#
# It would be "nice" to redesign the persistent store and use netstrings
# instead of Python pickling format, just for the sake of compatibility with
# other developpement environnements. Yet cPickle.dumps uses a well-defined
# text protocol and PNS/Persistence data structure is unambiguously flat,
# a simple hash of 8bit strings dictionnaries. Anyway, the PNS/Persistence
# store is better accessed via PNS protocols and the only reason to access
# it otherwise would be for system purpose (backup, migration, cleansing,
# bulk export, etc).
#
# By comparison, the PNS/Semantic persistent index and map are less complex
# but more specific data structures (just strings, but only public names)
# and using cPickle makes no sense as only a C pns_model module will really
# improve performances.
#
#
# Log
#
# Since every statements are cPickled in one big bsddb hash table, logging
# to a journal seems to be a sensible thing to do. Logging is delegated to
# the PNS_peer instance, asynchronously, as a single PNS session. See
# pns_peer.py for more on that.
