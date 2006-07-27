from allegra import (
    loginfo, async_loop, dns_client
    )
        
def resolved (request):
    loginfo.log ('%r' % (request.dns_resources, ), 'resolved')
        
dns_client.lookup (('www.google.be', 'A'), resolved)
dns_client.lookup (('google.be', 'MX'), resolved)
dns_client.lookup (('google.be', 'NS'), resolved)
dns_client.lookup ((
    '215.247.47.195.in-addr.arpa', 'PTR'
    ), resolved)
    
dns_client.first_mail_lookup ('google.be', resolved)

def reversed (ip):
    loginfo.log ('%r' % ip, 'reversed')
        
dns_client.reverse_lookup (
    'wwwfront.b-one.net', reversed
    )
    
async_loop.dispatch ()