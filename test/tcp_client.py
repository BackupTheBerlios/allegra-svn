from allegra import (
    loginfo, async_loop, async_chat, collector, tcp_client
    )

dispatcher = async_chat.Dispatcher ()
if tcp_client.connect (
    dispatcher, ("planetpython.org", 80), 3.0
    ):
    dispatcher.async_chat_push (
        'GET /rss20.xml HTTP/1.0\r\n'
        'Host: planetpython.org\r\n'
        'Accept: text/xml; charset=UTF-8\r\n'
        '\r\n'
        )
    collector.bind (dispatcher, collector.DEVNULL)
del dispatcher
async_loop.dispatch ()
#
# a convenience to ...
#
def getXMLUTF8 (
    dispatcher, host, path, 
    version="1.0", connection="Keep-Alive"
    ):
    dispatcher.async_chat_push (
        'GET %s HTTP/%s\r\n'
        'Host: %s\r\n'
        'Accept: text/xml; charset=UTF-8\r\n'
        'Connection: %s\r\n'
        '\r\n' % (path, version, host, connection)
        )
    return dispatcher
    
#
# ... use Connections and HTTP/1.0
#
connections = tcp_client.Connections (0.3, 0.1)
for host, path in [
    ("planetpython.org", "/rss20.xml"), 
    ("planet.python.org", "/rss20.xml"), 
    ]:
    collector.bind (getXMLUTF8 (connections (
        async_chat.Dispatcher (), (host, 80)
        ), host, path), collector.DEVNULL)
del connections
async_loop.dispatch ()
#
# ... or a Cache and HTTP/1.1
#
cache = tcp_client.Cache (0.3, 0.1)
dispatchers = set ((
    getXMLUTF8 (cache (
        async_chat.Dispatcher, (host, 80)
        ), host, path, "1.1")
    for host, path in (
        ("planetpython.org", "/rss20.xml"), 
        ("planet.python.org", "/rss20.xml"), 
        ("planetpython.org", "/rss.xml"), 
        ("planetpython.org", "/rdf.xml"), 
        ("planet.python.org", "/atom.xml"), 
        )
    ))
for dispatcher in dispatchers:
    collector.bind (dispatcher, collector.DEVNULL)
del dispatchers, dispatcher, cache
async_loop.dispatch ()