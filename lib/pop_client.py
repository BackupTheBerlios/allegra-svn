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

"http://laurentszyster.be/blog/pop_client/"

import socket

from allegra import collector, tcp_client, mime_reactor


class Pipeline (mime_reactor.Pipeline):
        
        def __init__ (self):
                mime_reactor.Pipeline.__init__ (self)
                def _POP3 (response):
                        assert None == self.log (response, 'POP3')
                        if response.startswith ('+OK'):
                                if self.pipeline_requests:
                                        self.pipeline_wake_up ()
                                return len (self.pipeline_responses) == 0
                        
                        self.handle_close ()
                        return True
                
                self.pipeline_responses.append ((
                        None, _POP3, '\r\n'
                        ))

        def __repr__ (self):
                return 'pop-pipeline id="%x"' % id (self)
                
        pop_capabilities = None
        
        def pop_capable (self, capable):
                if self.pop_capabilities != None:
                        capable ()
                        return
                        
                def _CAPA (response):
                        assert None == self.log (response, 'CAPA')
                        if response.startswith ('+OK'):
                                self.pop_capabilities = set (
                                        response.split ('\r\n')
                                        )
                                self.pipeline_pipeling = (
                                        'PIPELINING' in self.pop_capabilities
                                        )
                        capable ()
                        return False # tolerate no CAPA support
                        
                self.pipeline_requests.append (('CAPA\r\n', _CAPA, '\r\n.\r\n'))
        
        def pop_authorize (
                self, username, password, authorized, unauthorized
                ):
                def _USER (response):
                        assert None == self.log (response, 'USER')
                        if response.startswith ('+OK'):
                                def _PASS (response):
                                        assert None == self.log (
                                                response, 'PASS'
                                                )
                                        if response.startswith ('+OK'):
                                                authorized ()
                                        else:
                                                unauthorized ()
                                        return False
                                
                                self.pipeline_requests.append ((
                                        'PASS %s\r\n' % password, _PASS, '\r\n'
                                        ))
                        return False
        
                self.pipeline_requests.append ((
                        'USER %s\r\n' % username, _USER, '\r\n'
                        ))
                        
        def pop_retr (self, Collect):
                def _RETR (response):
                        assert None == self.log (response, 'RETR')
                        if response.startswith ('+OK'):
                                collect = Collect ()
                                if not collect.collector_is_simple:
                                        collect = collector.Simple (collect)
                                collector.bind_simple (
                                        self, mime_reactor.Escaping_collector (
                                                collect
                                                )
                                        )
                        return False
        
                return _RETR
        
        def pop_retr_one (self, order, Collect):
                self.pipeline_requests.append ((
                        'RETR %s\r\n' % order, 
                        self.pop_retr (Collect), 
                        '\r\n.\r\n'
                        ))
        
        
        def pop_retr_many (self, messages, Collect):
                _RETR = self.pop_retr (Collect)
                self.pipeline_requests.extend (((
                        'RETR %s\r\n' % order, _RETR, '\r\n.\r\n'
                        ) for order in messages))
        
        
        def pop_list_and_retr (dispatcher, Collect):
                "pipeline a LIST command, RETR all listed on success"
                def _LIST (response):
                        assert None == self.log (response, 'LIST')
                        if not response.startswith ('+OK'):
                                return True
                        
                        self.pop_retr_many ((
                                line.split (' ', 1)[0] 
                                for line in response.split ('\r\n')[1:]
                                ), Collect)
                        return False
        
                dispatcher.pipeline_requests.append ((
                        'LIST\r\n', _LIST, '\r\n.\r\n'
                        ))
        
        
        def pop_uidl_and_retr (self, afterUID, Collect):
                "pipeline a UIDL command, RETR all listed on success"
                def _UIDL (response):
                        assert None == self.log (response, 'UIDL')
                        if not response.startswith ('+OK'):
                                return True
                        
                        self.pop_retr_many ((order for order, uid in (
                                line.split (' ', 1)
                                for line in response.split ('\r\n')[1:]
                                ) if uid > afterUID), Collect)
                        return False
        
                self.pipeline_requests.append ((
                        'UIDL\r\n', _UIDL, '\r\n.\r\n'
                        ))
                        
        def pop_quit (self):
                self.pipeline_requests.append ((
                        'QUIT\r\n', (lambda r: False), None
                        ))
                
        def pop_quit_after_last (self):
                last = self.pipeline_requests.pop ()
                def _QUIT (response):
                        if last[1] (response):
                                return True
                        
                        self.pipeline_requests.append ((
                                'QUIT\r\n', (lambda r: False), None
                                ))
                        return False
                
                self.pipeline_requests.append ((last[0], _QUIT, last[2]))
                

def connect (host, port=110, timeout=3.0):
        dispatcher = Pipeline ()
        if tcp_client.connect (dispatcher, (host, port), timeout):
                return dispatcher
        
        return


# Note about this implementation
#
# The purpose of pop_client.py is to support asynchronous webmail: open
# a authenticated connection to a POP server, list a mailbox content, 
# fetch headers of new messages into a metabase, retrieve all messages, 
# save attachements separately and fetch their MIME headers as metadata.