import socket

from allegra import async_core, async_chat

class Proxy_server (async_core.Dispatcher):
    
    def __init__ (self, host, port):
        self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.there = (host, port)
        here = ('127.0.0.1', port + 8000)
        self.bind (here)
        self.listen (5)

    def handle_accept (self):
        Proxy_receiver (self, self.accept ())


class Proxy_sender (async_chat.Dispatcher):

    def __init__ (self, receiver, address):
        async_chat.Dispatcher.__init__ (self)
        self.receiver = receiver
        self.set_terminator (None)
        self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
        self.buffer = ''
        self.set_terminator ('\n')
        self.connect (address)

    def handle_connect (self):
        self.log ('connected', 'info')

    def collect_incoming_data (self, data):
        self.buffer = self.buffer + data

    def found_terminator (self):
        data = self.buffer
        if data: 
                self.log (data)
                self.buffer = ''
        self.receiver.async_chat_push (data + '\n')
        
    def handle_close (self):
        self.receiver.close ()
        self.close ()
         

class Proxy_receiver (async_chat.Dispatcher):

    channel_counter = 0

    def __init__ (self, server, (conn, addr)):
        async_chat.Dispatcher.__init__ (self)
        self.set_connection (conn, addr)
        self.set_terminator ('\n')
        self.server = server
        self.id = self.channel_counter
        self.channel_counter += 1
        self.sender = Proxy_sender (self, server.there)
        self.sender.id = self.id
        self.buffer = ''

    def collect_incoming_data (self, data):
        self.buffer += data
        
    def found_terminator (self):
        data = self.buffer
        if data: 
                self.log (data)
                self.buffer = ''
        self.sender.async_chat_push (data + '\n')

    def handle_close (self):
        self.log ('closing', 'info')
        self.sender.close ()
        self.close ()
         

if __name__ == '__main__':
    from allegra import loginfo, async_loop
    import sys
    if len(sys.argv) < 3:
        loginfo.log (
            'Usage: %s <server-host> <server-port>' % sys.argv[0],
            'fatal error'
            )
    else:
        ps = Proxy_server (sys.argv[1], int (sys.argv[2]))
        async_loop.dispatch ()