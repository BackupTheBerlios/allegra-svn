import socket

from allegra import (
        loginfo, async_loop, finalization, async_chat, async_client
        )

# test unmanaged client dispatcher

def test_unmanaged ():
        loginfo.log ('test_unmanaged')
        for host in ('999.999.999.999', '127.0.0.2', '127.0.0.1'):
                dispatcher = async_chat.Dispatcher ()
                if async_client.connect (dispatcher, (host, 80), 3):
                        dispatcher.async_chat_push (
                                'GET /prompt.xml HTTP/1.1\r\n'
                                'Host: %s\r\n'
                                '\r\n' % host
                                )
                else:
                        dispatcher.handle_close ()

test_unmanaged ()
async_loop.dispatch ()
finalization.collect ()

# test managed client dispatcher

def push (dispatcher, host):
        if not dispatcher.closing:
                dispatcher.async_chat_push (
                        'GET /prompt.xml?PRESTo=async&prompt=xdir(reactor)'
                        ' HTTP/1.1\r\n'
                        'Host: %s\r\n'
                        'Connection: keep-alive\r\n'
                        '\r\n' % host
                        )

def test_connections (connections, hosts):
        loginfo.log ('test_manager')
        for host in hosts:
                push (connections (
                        async_chat.Dispatcher (), (host, 80)
                        ), host)

def test_cache (cache, hosts):
        loginfo.log ('test_cache')
        for host in hosts:
                push (cache (async_chat.Dispatcher, host), host)
                        
def test_pool (pool):
        loginfo.log ('test_pool')
        for i in range (3):
                push (pool (), pool.client_name[0])

hosts = ('999.999.999.999', '127.0.0.2', '127.0.0.1')

def test_managed ():
        test_connections (connections, hosts)
        async_loop.dispatch ()
        finalization.collect ()
        test_cache (cache, hosts)
        async_loop.dispatch ()
        finalization.collect ()
        test_pool (pool)
        async_loop.dispatch ()
        finalization.collect ()

loginfo.log ('test_managed')

connections = async_client.Connections (3, 1)
cache = async_client.Cache (3, 1)
pool = async_client.Pool (
        async_chat.Dispatcher, (hosts[-1], 80), 2, 3, 1
        )
test_managed ()

loginfo.log ('test_limited')

connections = async_client.Connections (6, 1)
cache = async_client.Cache (6, 1)
pool = async_client.Pool (
        async_chat.Dispatcher, (hosts[-1], 80), 2, 6, 1
        )
for client in (connections, cache, pool):
        async_client.limited (client, 6, (lambda: 1024), (lambda: 1024))
test_managed ()

loginfo.log ('test_rationed')

connections = async_client.Connections (6, 1)
cache = async_client.Cache (6, 1)
pool = async_client.Pool (
        async_chat.Dispatcher, (hosts[-1], 80), 2, 6, 1
        )
for client in (connections, cache, pool):
        async_client.rationed (client, 6, 4096, 4096)
test_managed ()
