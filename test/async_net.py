# you'll need a PIRP and QMTP server running on localhost, or change the
# sources to match your test environment ...

import collections

from allegra import (
    async_loop, async_net, collector, async_client
    )
    
    
# Logging QMTP client

class QMTP (async_net.Dispatcher):
            
    ac_in_buffer_size = 1024
    ac_out_buffer_size = 1<<14
    
    def async_net_continue (self, string):
        code = string[0]
        if code == 'K':
            self.log (string)
        elif code == 'Z':
            self.log (string, 'temporary failure')
        elif code == 'D':
            self.log (string, 'permanent failure')
        else:
            self.log (string, 'protocol error')

qmtp = QMTP ()
if async_client.connect (qmt, ('127.0.0.1', 209), 3):
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
    async_loop.dispatch ()
    
    
# Logging PIRP client
    
class PIRP (async_net.Dispatcher):
            
    ac_in_buffer_size = 1<<14
    ac_out_buffer_size = 2048

    def __init__ (self):
        self.pirp_collectors = collections.deque ()
        async_net.Dispatcher.__init__ (self)
        
    def pirp_resolve (self, names, collector): 
        self.async_net_push (names)
        self.pirp_collectors.append (collector)

    def async_net_collect (self, data):
        self.pirp_collectors[0].collect_incoming_data (data)

    def async_net_terminate (self, data):
        c = self.pirp_collectors.popleft ()
        if data:
            c.collect_incoming_data (data)


pirp = PIRP ()
if async_client.connect (pirp, ('127.0.0.1', 553), 3):
    collect = collector.LOGINFO
    pirp.pirp_resolve (('index', 'html', ''), collect)
    pirp.pirp_resolve (('rss20', 'xml', ''), collect)
    async_loop.dispatch ()