import re # can't do without ;-)

from allegra import (
    finalization, async_chat, tcp_server, tcp_client
    )

LIST_TAGS = re.compile ('LIST TAGS ([0-9]+)')

class ZHUB (async_chat.Dispatcher):
        
    collected = ''
    tags = ['%s\r\n' % tag for tag in (
        'A', 'B', 'C', 'D', 'E', 'F', 'G'
        )]
    history = len (tags)
        
    def __init__ (self):
        async_chat.Dispatcher.__init__ (self)
        self.async_chat_push ('+OK 0.1 TEST\r\n')
        self.set_terminator ('\r\n')
        self.collected = ''
        
    def collect_incoming_data (self, data):
        self.collected += data
        
    def found_terminator (self):
        line = self.collected
        self.collected = ''
        m = LIST_TAGS.match (line)
        if m:
            requested = max (10, int (m.group (1)))
            returned = min (10, self.history)
            lines = ['+OK 200 LIST TAGS %d/%d/%d\r\n' % (
                requested, returned, self.history
                )]
            lines.extend (self.tags[:returned])
            self.async_chat_push (''.join (lines))
        else:
            self.async_chat_push ('+ERROR 400\r\n')
        self.close_when_done ()
        return True


LIST_TAGS_OK = re.compile (
    "[+]OK 200 LIST TAGS ([0-9]+)/([0-9]+)/([0-9]+)"
    )

def zhub_list (tags, count=0):
    # handle connect
    info = (yield ('', '\r\n', None))
    line = (yield ('LIST TAGS %d\r\n' % count, '\r\n', None))
    m = LIST_TAGS_OK.match (line)
    if m:
        returned = int (m.group (2))
        while returned > 0:
            returned -= 1
            line = (yield)
            tags.append (line)
    yield 
    # handle close
        
def main (
    count=0, host='127.0.0.2', port=14000, timeout=3.0, precision=1.0
    ):
    # server
    async_loop.catch (tcp_server.Listen (
        ZHUB, (host, port), precision, 5
        ).server_shutdown)
    # client
    tags = []
    zhub = async_chat.Trempoline ()
    zhub.protocol = zhub_list (tags, count)
    
    def finalize (dispatcher):
        if dispatcher.closing:
            dispatcher.log (tags, 'ok')
        else:
            dispatcher.log ('failed to connect', 'error')

    zhub.finalization = finalize
    tcp_client.connect (zhub, (host, port), timeout)
    del zhub

    
if __name__ == '__main__':
    import sys
    from allegra import async_loop, finalization, anoption
    anoption.cli (main, sys.argv[1:])
    async_loop.dispatch ()
    assert None == finalization.collect ()    