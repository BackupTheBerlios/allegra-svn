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

from allegra.sync_stdio import Sync_prompt
from allegra.tcp_client import TCP_client_channel
from allegra.netstring import \
        Netstring_collector, netstrings_encode, netstrings_decode
from allegra.pns_model import pns_name
from allegra.pns_sat import pns_sat_utf8


class PNS_prompt (Sync_prompt):

        def pns_peer (self, encoded):
                self.sync_stdout (encoded)
                self.sync_stderr ('\n')
                self.thread_loop_queue.push (self.sync_stdin)

        def sync_stdin (self):
                # get the subject, predicate, object and context
                model = []
                self.sync_stderr ("'-> ")
                model.append (sys.stdin.readline ()[:-1])
                self.sync_stderr ("  > ")  
                model.append (sys.stdin.readline ()[:-1])
                self.sync_stderr ("  > ")
                model.append (sys.stdin.readline ()[:-1])
                self.sync_stderr ("  > ")
                model.append (sys.stdin.readline ()[:-1])
                self.sync_stderr ("\n")
                if model[3]:
                        model[3] = pns_sat_utf8 (model[3])
                if model[0]:
                        model[0] = pns_sat_utf8 (model[0])
                else:
                        if model[1]:
                                model[1] = pns_sat_utf8 (model[1])
                        if model[2]:
                                model[2] = pns_sat_utf8 (model[2])
                self.select_trigger (self.sync_prompt)
                self.select_trigger (
                        lambda
                        m=self.pns_client.pns_statement_push, 
                        d=model:
                        m (d)
                        )
                if model[0] == model[1] == model[2] == '':
                        self.pns_client = None
                        
                        
class PNS_client (TCP_client_channel, Netstring_collector):
                
        pns_prompt = None
                
        def __init__ (self, ip):
                TCP_client_channel.__init__ (self, (ip, 3534))
                Netstring_collector.__init__ (self)
                self.tcp_connect ()
                
        collect_incoming_data = Netstring_collector.collect_incoming_data 
        found_terminator = Netstring_collector.found_terminator 

        def netstring_collector_error (self):
                assert None == self.log ('<netstring-error/>', '')
                self.close ()
                
        def netstring_collector_continue (self, encoded):
                self.pns_peer (encoded)
                self.netstring_collector_continue = self.pns_statement_pop

        def pns_peer (self, encoded):
                self.pns_prompt = PNS_prompt ()
                self.pns_prompt.pns_client = self
                self.pns_prompt.thread_loop_queue.push (
                        lambda p=self.pns_prompt.pns_peer, e=encoded: p (e)
                        )
                self.pns_prompt.start ()
                                
        def pns_statement_pop (self, encoded):
                self.pns_prompt.thread_loop_queue.push (
                        lambda
                        m=self.pns_prompt.sync_stdout,
                        d=(encoded+'\n'):
                        m (d)
                        )
                                
        def pns_statement_push (self, model):
                encoded = netstrings_encode (model)
                self.push ('%d:%s,' % (len (encoded), encoded))

        def close (self):
                TCP_client_channel.close (self)
                if self.pns_prompt:
                        self.pns_prompt.async_stdio_stop ()
                        self.pns_prompt = None

                                
if __name__ == '__main__':        
        import sys
        assert None == sys.stderr.write (
                'Allegra PNS/TCP Prompt'
                ' - Copyright 2005 Laurent A.V. Szyster\n'
                )
        if len (sys.argv) > 1:
                PNS_client (sys.argv[1])
        else:
                PNS_client ('127.0.0.1')
        from allegra import async_loop
        try:
                async_loop.loop ()
        except:
                async_loop.loginfo.loginfo_traceback ()
                