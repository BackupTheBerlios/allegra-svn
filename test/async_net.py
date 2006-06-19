# you'll need a PIRP and QMTP server running on localhost, or change the
# sources to match your test environment ...

import collections

from allegra.async_loop import dispatch
from allegra.async_net import Dispatcher
from allegra.tcp_client import TCP_client_channel


class QMTP_client_channel (Dispatcher, TCP_client_channel):
            
    ac_in_buffer_size = 1024
    ac_out_buffer_size = 1<<14
    
    def async_net_continue (self, string):
        code = string[0]
        if code == 'K':
            loginfo.log (string)
        elif code == 'Z':
            loginfo.log (string, 'temporary failure')
        elif code == 'D':
            loginfo.log (string, 'permanent failure')
        else:
            loginfo.log (string, 'protocol error')

qmtp = QMTP_client_channel ()
if qmtp.tcp_connect (('127.0.0.1', 209)):
    push = qmtp.output_fifo.append
    push ((
        'Subject: Hello\n\nHello who?', 
        'from@me', 
        netstring.encode (('to@you', ))
        ))
    push ((
        'Subject: Re: Hello\n\nHello World!', 
        '',
        netstring.encode (('to@you', 'cc@somebody'))
        ))
    dispatch ()

    
class PIRP_client_channel (Dispatcher, TCP_client_channel):
            
    ac_in_buffer_size = 1<<14
    ac_out_buffer_size = 2048

    def __init__ (self):
        self.pirp_collectors = collections.deque ()
        Async_net.__init__ (self)
        
    def pirp_resolve (self, names, collector): 
        self.async_net_push (names)
        self.pirp_collectors.append (collector)

    def async_net_collect (self, data):
        self.pirp_collectors[0].collect_incoming_data (data)

    def async_net_terminate (self, data):
        c = self.pirp_collectors.popleft ()
        if data:
            c.collect_incoming_data (data)


pirp = PIRP_client_channel ()
if pirp.tcp_connect (('127.0.0.1', 553)):
    from allegra.collector import Loginfo_collector
    collect = Loginfo_collector ()
    pirp.pirp_resolve (('index', 'html', ''), collect)
    pirp.pirp_resolve (('rss20', 'xml', ''), collect)
    dispatch ()