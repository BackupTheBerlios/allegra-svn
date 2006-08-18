import sys

from allegra import async_loop, async_core, async_client

try:
        TCP_CONCURRENT = max (1, int (sys.argv[1]))
except:
        TCP_CONCURRENT = 64
try:
        TCP_WINDOW_SIZE = 1 << min (14, int (sys.argv[2]))
except:
        TCP_WINDOW_SIZE = 1 << 14
TCP_OVERFLOW_DATA = 'x' * (TCP_WINDOW_SIZE*2)

class Flaking (async_core.Dispatcher):
        
        def handle_write (self):
                self.send (TCP_OVERFLOW_DATA)
                
        def handle_read (self):
                self.recv (TCP_WINDOW_SIZE/2)
                

for i in range (TCP_CONCURRENT):
        async_client.connect (Flaking (), ('127.0.0.1', 1234), 3)

async_loop.dispatch ()