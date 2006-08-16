import time

from allegra import (
    loginfo, async_loop, dns_client
    )
        
def test_lookup (info):
        def resolved (request):
            loginfo.log ('%r' % (request.__dict__, ), info)
        
        # lookup A, MX, NS and PTR resource records
        dns_client.lookup (('www.google.be', 'A'), resolved)
        dns_client.lookup (('google.be', 'MX'), resolved)
        dns_client.lookup (('google.be', 'NS'), resolved)
        dns_client.lookup ((
            '215.247.47.195.in-addr.arpa', 'PTR'
            ), resolved)
        # lookup the same question twice
        dns_client.lookup (('www.google.be', 'A'), resolved)
        # try an error
        dns_client.lookup (('www.google', 'A'), resolved)
        # and failing server/IP addresses
        dns_client.lookup (('www.google.com', 'A'), resolved, (
                '192.168.1.3', 'not-a-valid-IP-address', '192.168.1.1', 
                ))
        
# test asap
test_lookup ('resolved')
# schedule cache hits
def delayed_lookup (when):
        test_lookup ('delayed')
async_loop.schedule (time.time () + 6, delayed_lookup)
    
async_loop.dispatch ()