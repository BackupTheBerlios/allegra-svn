import socket

from allegra import loginfo, async_loop, async_chat, async_client

class Chat (async_chat.Async_chat, async_client.Dispatcher):
        terminator = None
        
# test unmanaged client dispatcher

def test_unmanaged ():
        loginfo.log ('test_unmanaged')
        for host in ('999.999.999.999', '127.0.0.2', '127.0.0.1'):
                dispatcher = Chat ()
                if dispatcher.client_connect ((host, 80), timeout=3):
                        dispatcher.async_chat_push (
                                'GET /prompt.xml HTTP/1.1\r\n'
                                'Host: %s\r\n'
                                '\r\n' % host
                                )
                else:
                        dispatcher.handle_close ()

test_unmanaged ()
async_loop.dispatch ()

# test managed client dispatcher

def test_managed (dispatcher, host):
        if not dispatcher.closing:
                dispatcher.async_chat_push (
                        'GET /prompt.xml HTTP/1.1\r\n'
                        'Host: %s\r\n'
                        'Connection: keep-alive\r\n'
                        '\r\n' % host
                        )

def test_manager (manager, hosts):
        loginfo.log ('test_manager')
        for host in hosts:
                test_managed (manager (Chat (), (host, 80)), host)

def test_cache (cache, hosts):
        loginfo.log ('test_cache')
        for host in hosts:
                test_managed (cache (Chat, host), host)
                        
def test_pool (pool):
        loginfo.log ('test_pool')
        for i in range (3):
                test_managed (pool (), pool.client_name[0])

hosts = ('999.999.999.999', '127.0.0.2', '127.0.0.1')
manager = async_client.Manager (3, 1)
cache = async_client.Cache (3, 1)
pool = async_client.Pool (Chat, (hosts[-1], 80), 2, 3, 1)

loginfo.log ('test_managed')

test_manager (manager, hosts)
async_loop.dispatch ()
test_cache (cache, hosts)
async_loop.dispatch ()
test_pool (pool)
async_loop.dispatch ()

loginfo.log ('test_limited')

for client in (manager, cache, pool):
        async_client.limited (client, 3, (lambda: 1024), (lambda: 1024))
test_manager (manager, hosts)
async_loop.dispatch ()
test_cache (cache, hosts)
async_loop.dispatch ()
test_pool (pool)
async_loop.dispatch ()

for client in (manager, cache, pool):
        async_client.rationed (client, 3, 1024, 1024)
test_manager (manager, hosts)
async_loop.dispatch ()
test_cache (cache, hosts)
async_loop.dispatch ()
test_pool (pool)
async_loop.dispatch ()

