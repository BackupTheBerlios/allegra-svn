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

import socket

from allegra import collector, tcp_client, mime_reactor


class Pipeline (mime_reactor.Pipeline):
        
        collector_stalled = True
        
        pop_capabilities = set (('STAT', 'LIST', 'RETR', 'DELE'))

        def __repr__ (self):
                return 'pop-pipeline id="%x"' % id (self)
                
        def pop_capable (self):
                def _CAPA (response):
                        if response.startswith ('+OK'):
                                self.pop_capabilities = set (
                                        response.split ('\r\n')
                                        ).union (self.pop_capabilites)
                                self.pipeline_pipeling = (
                                        'PIPELINING' in self.pop_capabilities
                                        )
                        return False # tolerate no CAPA support
                        
                self.pipeline_requests.append (('CAPA\r\n', CAPA, '\r\n'))
        
        def pop_authorize (
                self, username, password, authorized,
                unauthorized=(lambda d: d.handle_close ())
                ):
                def _USER (response):
                        if not response.startswith ('+OK'):
                                unauthorized (self)
                                return True
                
                        def _PASS (response):
                                if not response.startswith ('+OK'):
                                        unauthorized (self)
                                        return True
                                
                                authorized (self)
                                return False
                        
                        self.pipeline_requests.append ((
                                'PASS %s\r\n' % password, _PASS, '\r\n'
                                ))
                        return False
        
                self.pipeline_requests.append ((
                        'USER %s\r\n' % username, _USER, '\r\n'
                        ))
        
        def pop_retr (self, order, collect):
                def _RETR (response):
                        if not response.startswith ('+OK'):
                                return False
                        
                        if not collect.collector_is_simple:
                                collect = collector.Simple (collect)
                        collector.bind_simple (
                                self, mime_reactor.Escaping_collector (collect)
                                )
                        return False
        
                self.pipeline_requests.append ((
                        'RETR %s\r\n' % order, _RETR, '\r\n.\r\n'
                        ))
        
        
        def pop_retr_many (self, messages, Collect):
                def _RETR (response):
                        if not response.startswith ('+OK'):
                                return False
                        
                        collect = Collect ()
                        if not collect.collector_is_simple:
                                collect = collector.Simple (collect)
                        collector.bind_simple (
                                self, mime_reactor.Escaping_collector (collect)
                                )
                        return False
        
                self.pipeline_requests.extend (((
                        'RETR %s\r\n' % order, _RETR, '\r\n.\r\n'
                        ) for order in messages))
        
        
        def pop_list_and_retr (dispatcher, Collect):
                "pipeline a LIST command, RETR all listed on success"
                def _LIST (response):
                        if not response.startswith ('+OK'):
                                return True
                        
                        self.pop_retr_many ((
                                line.split (' ', 1)[0] 
                                for line in response.split ('\r\n')
                                ), Collect)
                        return False
        
                dispatcher.pipeline_requests.append ((
                        'LIST\r\n', _LIST, '\r\n.\r\n'
                        ))
        
        
        def pop_uidl_and_retr (dispatcher, Collect):
                "pipeline a UIDL command, RETR all listed on success"
                def _UIDL (response):
                        if not response.startswith ('+OK'):
                                return True
                        
                        self.pop_retr_many ((
                                line.split (' ', 1)[0] 
                                for line in response.split ('\r\n')
                                ), Collect)
                        return False
        
                self.pipeline_requests.append ((
                        'UIDL\r\n', _UIDL, '\r\n.\r\n'
                        ))


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