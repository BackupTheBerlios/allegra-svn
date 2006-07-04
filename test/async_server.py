import socket

from allegra import (
    async_loop, finalization,
    async_net, async_chat, async_server
    )
        
loglines = async_server.Listen (
    async_chat.Dispatcher, ('127.0.0.1', 1234),
    6, 5, socket.AF_INET 
    )
async_loop.catch (loglines.server_shutdown)
del loglines
    
lognet = async_server.Listen (
    async_net.Dispatcher, ('127.0.0.1', 2345),
    6, 5, socket.AF_INET 
    )
async_server.accept_named (lognet, 512)
async_server.inactive (lognet, 6)
async_loop.catch (lognet.server_shutdown)
del lognet
    
loglines = async_server.Listen (
    async_chat.Dispatcher, ('127.0.0.1', 3456),
    3, 5, socket.AF_INET 
    )
loglines.server_resolved = (lambda addr: addr[0])
async_server.accept_named (loglines, 2)
async_server.rationed (loglines, 6, 1<<14, 1<<16)
async_loop.catch (loglines.server_shutdown)
del loglines

async_loop.dispatch ()
finalization.collect ()