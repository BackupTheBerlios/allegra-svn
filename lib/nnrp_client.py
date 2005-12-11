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

import time

from allegra import \
        loginfo, finalization, async_chat, tcp_client, \
        dns_client, mime_headers, mime_reactor


class NNRP_client_channel (
        tcp_client.Pipeline, mime_reactor.MIME_collector,
        tcp_client.TCP_client, async_chat.Async_chat
        ):
                
        def __init__ (self):
                tcp_client.Pipeline.__init__ (self)
                async_chat.Async_chat.__init__ (self)
                self.set_terminator ('\r\n')
                
        def mime_collector_continue (self):
                nnrp_response = self.mime_collector_lines[0][:3]
                if nnrp_response in ('205', '400'):
                        handle_close ()
                        return
                        
                if nnrp_response in  ('200', '201'):
                        self.pipeline_wake_up ()
                        return
                        
                if nnrp_response == '':
                        pass
                        
        def nnrp_user (self, name, password):
                pass
                
        def nnrp_group (self, name):
                pass
                
        def nnrp_article (self, id, collector=None):
                pass
                
        def nnrp_stat (self, id, collector=None):
                pass
                
        def nnrp_head (self, id, collector=None):
                pass
                
        def nnrp_body (self, id, collector=None):
                pass
    
        
# A simple NNRP client channel
#
#        news = NNRP_client_channel ('use.net')
#
# four interfaces
#
#        list = news.nnrp_list ()
#        group = news.nnrp_group ()
#        group.nnrp_next ()
#
#        stat = news.nnrp_stat (nnn)
#        article = news.nnrp_article ('id')
#        head = news.nnrp_head ('id')
#        body = news.nnrp_body ('id')
#
# that return the appropriate reactor, and one newsfeed articulator
#
#        group.feed ('comp.lang.python', pipe)
#
# that pipelines everything