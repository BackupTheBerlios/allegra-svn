import socket

from allegra import async_loop, async_chat, async_client

class Chat (async_chat.Async_chat, async_client.Dispatcher):
        terminator = None
        
# test unmanaged client dispatcher

for host in ('999.999.999.999', '127.0.0.2', '127.0.0.1'):
        dispatcher = Chat ()
        if dispatcher.client_connect ((host, 80), timeout=3):
                dispatcher.async_chat_push (
                        'GET /prompt.xml HTTP/1.1\r\n'
                        'Host: %s'
                        '\r\n' % host
                        )
        else:
                dispatcher.handle_close ()
del dispatcher

async_loop.dispatch ()

# test managed client dispatcher

def test_managed (manager, host):
        dispatcher = Chat ()
        if manager.client_connect (dispatcher, (host, 80)):
                dispatcher.async_chat_push (
                        'GET /prompt.xml HTTP/1.1\r\n'
                        'Host: %s'
                        'Connection: keep-alive\r\n'
                        '\r\n' % host
                        )
        else:
                dispatcher.handle_close ()

manager = async_client.Manager (3, 1)
for host in ('999.999.999.999', '127.0.0.2', '127.0.0.1'):
        test_managed (manager, host)

async_loop.dispatch ()