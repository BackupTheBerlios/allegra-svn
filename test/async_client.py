import socket

from allegra import async_loop, async_chat, async_client

class Chat (async_chat.Async_chat, async_client.Dispatcher):
        terminator = None
        
dispatcher = Chat ()
if dispatcher.client_connect (
        ('127.0.0.1', 80), timeout=3
        ):
        dispatcher.async_chat_push (
                'GET /prompt.xml HTTP/1.1\r\n'
                'Host: 127.0.0.1\r\n'
                '\r\n'
                )
else:
        dispatcher.handle_close ()
        
dispatcher = Chat ()
if dispatcher.client_connect (
        ('999.999.999.999', 80), timeout=3
        ):
        dispatcher.async_chat_push (
                'GET /prompt.xml HTTP/1.1\r\n'
                'Host: 127.0.0.1\r\n'
                '\r\n'
                )
else:
        dispatcher.handle_close ()
        
async_loop.dispatch ()

client = async_client.Manager (Chat, 6, 1)
async_client.inactive (client, 12) #, lambda: 1024, lambda: 1024)
dispatcher = client (('999.999.999.999', 80))
if not dispatcher.closing:
        dispatcher.async_chat_push (
                'GET /prompt.xml HTTP/1.1\r\n'
                'Host: 127.0.0.1\r\n'
                'Connection: keep-alive\r\n'
                '\r\n'
                )
        
dispatcher = client (('127.0.0.2', 80))
if not dispatcher.closing:
        dispatcher.async_chat_push (
                'GET /prompt.xml HTTP/1.1\r\n'
                'Host: 127.0.0.1\r\n'
                'Connection: keep-alive\r\n'
                '\r\n'
                )
        
dispatcher = client (('127.0.0.1', 80))
if not dispatcher.closing:
        dispatcher.async_chat_push (
                'GET /prompt.xml?PRESTo=async&prompt=xdir(reactor) HTTP/1.1\r\n'
                'Host: 127.0.0.1\r\n'
                'Connection: keep-alive\r\n'
                '\r\n'
                )

del dispatcher

async_loop.dispatch ()