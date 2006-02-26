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

import glob, bsddb, cPickle
#
# TODO: maybe replace cPickle by a faster dictionnary made of netstrings
#       and actually search for strings instead of instanciating hashes
#       ...
#

from allegra import netstring, thread_loop


class PNS_resolution (thread_loop.Thread_loop):

	pns_statements = None

	def __init__ (self, pns_peer):
		self.pns_peer = pns_peer
		self.pns_root = self.pns_peer.pns_root
		thread_loop.Thread_loop.__init__ (self)
		self.start ()
		
	def __repr__ (self):
		return 'pns_resolution'
		
	def thread_loop_init (self):
        	if glob.glob (self.pns_root + '/statements.log'):
        		self.pns_log_file = open (
        			self.pns_root + '/statements.log', 
        			'a'
        			)
   		else:
   			self.pns_log_file = open (
        			self.pns_root + '/statements.log', 
        			'w'
        			)
                try:
                        self.pns_statements = bsddb.db.DB ()
                        if glob.glob (self.pns_root + '/statements.db'):
                        	self.pns_statements.open (
                        		self.pns_root + '/statements.db'
                        		)
                  	else:
                        	self.pns_statements.open (
                        		self.pns_root + '/statements.db',
                        		dbtype=bsddb.db.DB_HASH,
                        		flags=bsddb.db.DB_CREATE
                        		)
                except:
                        self.select_trigger_traceback ()
                        return False
                        
                else:
                        assert None == self.select_trigger_log (
                        	'opened', 'debug'
                        	)
                return True

	def thread_loop_delete (self):
                if self.pns_statements != None:
                        try:
                                self.pns_statements.close ()
                        except:
                                self.select_trigger_traceback ()
                        else:
                                del self.pns_statements
                        	assert None == self.select_trigger_log (
                        		'closed', 'debug'
                        		)
                self.select_trigger ((
                	self.pns_peer.pns_resolution_finalize, ()
                	))
                del self.pns_peer
                return True
                
	# Resolution

	def pns_log (self, model):
		encoded = netstring.encode (model)
		self.pns_log_file.write (
			'%d:%s,' % (len (encoded), encoded)
			)

	def pns_resolve (self, model):
		# store, retrieve and update, but also filter statements,
		# returns a tuple (persistent, stored), indicating wether
		# the statement is to be blocked and the object stored
		# previously if any.
		#
                sp = netstring.encode (model[:2])
                stored = self.pns_statements.get (sp)
                if stored == None:
                	# new (subject, predicate): log, store and pass
                	assert None == self.select_trigger_log (
                		netstring.encode (model), 'new'
                		)
                	self.pns_log (model)
			self.pns_statements [sp] = cPickle.dumps (
				{model[3]: model[2]}
				)
			return True, None

		# load the {(object, context)} hash from the store
		persistents = cPickle.loads (stored)
		o = persistents.get (model[3])
		if o == model[2]:
			# redundant contextual statement: block
                	assert None == self.select_trigger_log (
                		netstring.encode (model), 'block'
                		)
			return False, None
			
		if model[2] != '':
			# dissent: log, update answer and pass
                	assert None == self.select_trigger_log (
                		netstring.encode (model), 'update'
                		)
                	self.pns_log (model)
			persistents[model[3]] = model[2]
			self.pns_statements[sp] = cPickle.dumps (persistents)
		return True, o
		
        # PNS/TCP open questions and named statements
        
	def pns_anonymous (self, model):
		# anonymous question, resolve in all contexts.
                sp = netstring.encode (model[:2])
                stored = self.pns_statements.get (sp)
                if stored != None:
	          	bounce = model[:5]
	          	bounce[2] = netstring.encode ([
				netstring.encode (i) 
				for i in cPickle.loads (stored).items ()
				])
			self.select_trigger ((
				self.pns_peer.pns_tcp_continue,
				(bounce, '_')
				))
		self.select_trigger ((
			self.pns_peer.pns_tcp_continue, (model, '.')
			))
		#
		# why not do anonymous answers too? well, the only use
		# for such syntax would be to find the context for a
		# given (subject,predicate,object) triple, which is
		# anyway provided by a more general (subject,predicate,)
		# question.
		
	def pns_statement (self, model):
		dissent, stored = self.pns_resolve (model)
		if dissent:
			if stored:
				# bounce any persistent statement stored
				# for the same subject, predicate and context
				# as this statement
				#
		          	bounce = model[:5]
		          	bounce[2] = stored
				self.select_trigger ((
					self.pns_peer.pns_tcp_continue,
					(bounce, '_')
					))
			# let the peer continue this statement, try to relay
			# or route it to a subscribed context
			#
			self.select_trigger ((
				self.pns_peer.pns_statement_continue, 
				(model,)
				))
		else:
			# redundant statement, echo request handling to the
			# user agent.
			#
			self.select_trigger ((
				self.pns_peer.pns_tcp_continue,
				(model, '.')
				))

	# PNS/UDP circle

	def pns_pirp (self, name, addr):
		# bounce back a persistent protocol answer to the peer
		#
		encoded = '%d:%s,0:,' % (len (name), name)
		dissent, left = self.pns_resolve (
			(name, '', '', name)
			)
		if dissent and left:
			encoded += '%d:%s,' % (len (left), left)
		else:
			encoded += '0:,'
		self.select_trigger ((
			self.pns_peer.pns_pirp_continue,
			(name, encoded, addr)
			))
		#
		# this is PIRP, restricted to PNS/UDP protocol questions.

	def pns_out_of_circle (self, name):
		# either join the last persistent right peer, or
		# route a protocol question
		#
		model = [name, '', '', name]
		dissent, left = self.pns_resolve (model)
		if left == None:
			self.select_trigger ((
				self.pns_peer.pns_inference.pns_statement,
				(model,)
				))
			return
			
		self.select_trigger ((
			self.pns_peer.pns_join_continue, (name, left)
			))
			
	def pns_question (self, model):
		# check persistence, bounce answer and route dissent
		dissent, stored = self.pns_resolve (model)
		if dissent:
			if stored:
				bounce = model[:]
				bounce[2] = stored
				self.select_trigger ((
					self.pns_peer.pns_statement_continue,
					(bounce,)
					))
			self.select_trigger ((
				self.pns_peer.pns_inference.pns_statement,
				(model,)
				))
			
	def pns_answer (self, model):
		dissent, stored = self.pns_resolve (model)
		if dissent:
			self.select_trigger ((
				self.pns_peer.pns_inference.pns_statement,
				(model,)
				))		
	
	# asynchronous interfaces
		
        def pns_tcp_anonymous (self, *args):
        	self.thread_loop_queue ((self.pns_anonymous, args))
                
	def pns_tcp_statement (self, *args):
        	self.thread_loop_queue ((self.pns_statement, args))
		
	def pns_udp_pirp (self, *args):
		self.thread_loop_queue ((self.pns_pirp, args))

	def pns_udp_out_of_circle (self, *args):
		self.thread_loop_queue ((self.pns_out_of_circle, args))

	def pns_udp_question (self, *args):
		self.thread_loop_queue ((self.pns_question, args))

	def pns_udp_answer (self, *args):
		self.thread_loop_queue ((self.pns_answer, args))

		
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
