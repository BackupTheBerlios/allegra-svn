import sys

from allegra import async_loop, async_core, async_server

try:
        TCP_WINDOW_SIZE = 1 << int (sys.argv[1])
except:
        TCP_WINDOW_SIZE = 1 << 14
TCP_OVERFLOW_DATA = 'x' * (TCP_WINDOW_SIZE*2)

class Flaking (async_core.Dispatcher):
        
        def handle_write (self):
                self.send (TCP_OVERFLOW_DATA)
                
        def handle_read (self):
                self.recv (TCP_WINDOW_SIZE/2)
                
        def close_when_done (self):
                self.close ()
                
flaking = async_server.Listen (
        Flaking, ('127.0.0.1', 1234), 6, 5
        )
async_loop.catch (flaking.server_shutdown)        
async_loop.dispatch ()