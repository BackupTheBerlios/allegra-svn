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

import re, time, quopri

from allegra import (
        loginfo, finalization, async_chat, async_client, 
        dns_client, mime_headers, mime_reactor
        )
        
class Reactor (finalization.Finalization):

        nnrp_group = nnrp_request = nnrp_response = nnrp_collector = None

# reactor = Reactor ()
# reactor.nnrp_request = 'GROUP ...'
# def finalize (reactor):
#         reactor.nnrp_response
#         reactor.nnrp_collector
# reactor.finalization = finalize
# connect.pipeline (reactor)
# ...
#
# in API
#
# from allgra import nnrp_client
#
# nnrp = nnrp_client.Pool (('192.168.1.1', '119'), 2)
# def finalize (reactor):
# ...
# r = nnrp.LIST ()
# r = nnrp.GROUP ('group')
# r = nnrp.STAT ('group')
# r = nnrp.POST ('group', mime_headers, mime_body_producer)
# r = nnrp.HEAD (id)
# r = nnrp.ARTICLE (id, mime_body_collector)
# 
# r.finalization = ...
#
# Just enough to develop a simple agent, with a synchronized BSDDB backend
# to store headers a BSDBD hash table of ids, BTREE indexes for any headers 
# and articles in a RECORD queue.
#
# nnrp_client.harvest (
#        addr=('localhost', 119), 
#        root='.', groups=['GROUP', ...]
#        )
#
# ready for derivation and an HTTP front-end to flat web of MIME resources.

class Dispatcher (
        mime_reactor.MIME_collector,
        async_chat.Dispatcher,
        async_client.Dispatcher,
        async_client.Pipeline
        ):
                
        nnrp_username = nnrp_password
                
        def __init__ (self):
                async_chat.Dispatcher.__init__ (self)
                self.set_terminator ('\r\n')
                
        def handle_connect (self):
                pass # send user name and password if any ...
                
        def mime_collector_continue (self):
                nnrp_response = self.mime_collector_lines[0][:3]
                if nnrp_response in ('205', '400'):
                        self.handle_close ()
                        return True # collector stalled
                        
                if nnrp_response in  ('200', '201'):
                        self.pipeline_wake_up ()
                        return False
                
        def mime_collector_finalize (self):
                # self.mime_body_collector.found_terminator ()
                # self.mime_body_collector = None
                # self.async_client.nnrp_collect (
                #        self.pipeline_responses.popleft ()
                #        )
                return False
                
        def pipeline_push (self):
                pass
        
        def nnrp_group (self, name):
                self.async_chat_push ('GROUP %s\n' % name)
                
        def nnrp_stat (self, id, collector=None):
                self.async_chat_push ('STAT %s\n' % name)
                
        def nnrp_article (self, id, collector=None):
                pass

        def nnrp_head (self, id, collector=None):
                pass
                
        def nnrp_body (self, id, collector=None):
                pass


class Agent (async_client.Pool):
        
        pass

# Note about this implementation
#
# Just enough of an USENET client to retrieve one or all articles from
# a given newsgroup, decode Quoted Printable headers and collect it. 