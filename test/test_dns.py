from allegra import (
    loginfo, async_loop, dns_client
    )
        
def resolved (request):
    loginfo.log ('%r' % (request.__dict__, ), 'resolved')
        
dns_client.lookup (('www.google.be', 'A'), resolved)
dns_client.lookup (('google.be', 'MX'), resolved)
dns_client.lookup (('google.be', 'NS'), resolved)
dns_client.lookup ((
    '215.247.47.195.in-addr.arpa', 'PTR'
    ), resolved)

# ask the same question twice

dns_client.lookup (('www.google.be', 'A'), resolved)

# force errors

dns_client.lookup (('www.google', 'A'), resolved)
dns_client.lookup (('www.google.com', 'A'), resolved, (
        '192.168.1.3', 'not-a-valid-IP-address', '192.168.1.1', 
        ))

# schedule cache hits

import time

def delayed_lookup (when):
        dns_client.lookup (('www.google.be', 'A'), resolved)
        dns_client.lookup (('google.be', 'MX'), resolved)
        dns_client.lookup (('google.be', 'NS'), resolved)
        dns_client.lookup ((
            '215.247.47.195.in-addr.arpa', 'PTR'
            ), resolved)

async_loop.schedule (time.time () + 6, delayed_lookup)
    
async_loop.dispatch ()