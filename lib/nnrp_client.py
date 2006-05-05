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
        loginfo, async_chat, tcp_client, 
        dns_client, mime_headers, mime_reactor
        )


class NNRP_client_channel (
        tcp_client.Pipeline,
        mime_reactor.MIME_collector,
        tcp_client.TCP_client_channel, 
        async_chat.Async_chat
        ):
                
        def __init__ (self):
                async_chat.Async_chat.__init__ (self)
                self.set_terminator ('\r\n')
                
        def mime_collector_continue (self):
                nnrp_response = self.mime_collector_lines[0][:3]
                if nnrp_response in ('205', '400'):
                        self.handle_close ()
                        return True
                        
                if nnrp_response in  ('200', '201'):
                        self.pipeline_wake_up ()
                        return False                        
                
        def mime_collector_finalize (self):
                return False
                        
        def nnrp_user (self, name, password):
                pass
                
        def nnrp_group (self, name):
                self.push ('GROUP %s\n' % name)
                
        def nnrp_stat (self, id, collector=None):
                self.push ('STAT %s\n' % name)
                
        def nnrp_article (self, id, collector=None):
                pass

        def nnrp_head (self, id, collector=None):
                pass
                
        def nnrp_body (self, id, collector=None):
                pass

# Note about this implementation
#
# Just enough of an USENET client to retrieve one or all articles from
# a given newsgroup, decode Quoted Printable headers and collect it. 