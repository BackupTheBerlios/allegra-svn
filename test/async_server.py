import socket

from allegra import async_net, async_server

listen = async_server.Listen (
    async_net.Dispatcher, ('127.0.0.1', 1234),
    256, 6, 5, socket.AF_INET 
    )
async_server.catch_shutdown (listen)
del listen

from allegra import async_loop, finalization

async_loop.dispatch ()
finalization.collect ()

# public

from allegra import async_chat

listen = async_server.Listen (
    async_chat.Dispatcher, ('0.0.0.0', 1234),
    2, 6, 5, socket.AF_INET 
    )
listen.server_resolved = (lambda addr: addr[0])
async_server.rationed (listen, 3, 1<<14, 1<<16)
async_server.catch_shutdown (listen)
del listen

async_loop.dispatch ()
finalization.collect ()