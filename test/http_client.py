import sys, time
from allegra import (
        loginfo, async_loop, producer, collector, tcp_client,
        http_client
        )
loginfo.log (
        'Allegra HTTP/1.1 Client'
        ' - Copyright 2005 Laurent A.V. Szyster'
        ' | Copyleft GPL 2.0', 'info'
        )
try:
        method, uri, version = sys.argv[1:4]
        method = method.upper ()
        protocol, url = uri.split ('//')
        host, path = url.split ('/', 1)
        addr = host.split (':')
        if len (addr) < 2:
                addr.append ('80')
        host, port = (addr[0], int(addr[1]))
except:
         sys.exit (1)

R = C = 1
urlpath = '/' + path
if method == 'POST':
        body = sys.argv[4]
        if len (sys.argv) > 5:
                R = int (sys.argv[5])
                if  len (sys.argv) > 6:
                        C = int (sys.argv[6])
elif method == 'GET' and len (sys.argv) > 4:
        R = int (sys.argv[4])
        if  len (sys.argv) > 5:
                C = int (sys.argv[5])
#
 # get a TCP pipeline connected to the address extracted from the
 # URL and push an HTTP reactor with the given command and URL path,
 # close when done ...
 #
if C*R > 1:
        collect = collector.DEVNULL
else:
        collect = collector.LOGINFO
t_instanciated = time.clock ()
http = http_client.Connections ()
for i in range (C):
        pipeline = http (host, port)
        for j in range (R):
                if method == 'GET':
                        http_client.GET (pipeline, urlpath) (collect)
                elif method == 'POST':
                        http_client.POST (
                                pipeline, urlpath, 
                                producer.Simple (body)
                                ) (collect)
        del pipeline
t_instanciated = time.clock () - t_instanciated
t_completed = time.clock ()
async_loop.dispatch ()
t_completed = time.clock () - t_completed
loginfo.log (
        'Completed in %f seconds, '
        'at the average rate of %f seconds per requests, '
        'or %f requests per seconds. '
        'Note that it took %f seconds to instanciate '
        'the %d client channels and %d requests.' % (
                t_completed, t_completed/(C*R), (C*R)/t_completed, 
                t_instanciated, C, R
                ), 'info'
        )
#
# Note:
#
# Network latency is usually so high that the DNS response will
# come back long after the program entered the async_loop. So it is
# safe to instanciate a named TCP pipeline and trigger asynchronous
# DNS resolution before entering the loop.


# Note about this implementation
#
# The purpose of Allegra's HTTP/1.1 client is to provide peers with a
# simple and fully non-blocking API for all methods: GET, POST, HEAD,
# PUT, etc.
#
# Synopsis
#
#        from allegra import synchronizer, http_client
#        http = http_client.HTTP_client ()
#        request = http ('planet.python.org').GET ('/rss20.xml', {
#                'Host': 'planet.python.org',
#                'Accept-Charset': 'iso-8559-1,utf-8;q=0.9,ascii;q=0.8',
#                }) (synchronizer.File (
#                        'planet.python.org-rss20.xml'
#                        ))
#