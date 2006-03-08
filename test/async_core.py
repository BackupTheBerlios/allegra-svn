from allegra import async_core
import socket
import string
        
class http_client (async_core.Async_dispatcher):
        
    def __init__ (self, host, path):
        async_core.Async_dispatcher.__init__ (self)
        self.path = path
        self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
        self.connect ((host, 80))
        
    def handle_connect (self):
        self.send ("GET %s HTTP/1.0\r\n\r\n" % self.path)
        
    def handle_read (self):
        data = self.recv (8192)
        self.log (data)
        
    def handle_write (self):
        pass
        
if __name__ == "__main__":
    from allegra import async_loop
    import sys
    import urlparse
    for url in sys.argv[1:]:
        parts = urlparse.urlparse (url)
        if parts[0] != "http":
            raise ValueError, "HTTP URLs only, please"
        else:
            host = parts[1]
            path = parts[2]
            http_client (host, path)
    async_loop.dispatch ()