import sys

from allegra import (
        netstring, loginfo, finalization, ip_peer, dns_client
        )

if len (sys.argv) < 2:
        assert None == loginfo.log (
                'nslookup.py NAME [TYPE=A [SERVER ...]]',
                'info'
                )
        sys.exit (1)
        
servers = None
if len (sys.argv) > 2:
        question = tuple (sys.argv[1:3])
        if len (sys.argv) > 3:
                servers = sys.argv[3:]
else:
        question = (sys.argv[1], 'A')
def resolved (request):
        model = list (request.dns_question)
        if request.dns_resources == None:
                model.append ('')
        elif len (request.dns_resources) > 1:
                model.append (netstring.encode (
                        request.dns_resources
                        ))
        elif request.dns_resources:
                model.append (request.dns_resources[0])
        else:
                model.append ('')
        model.append (request.dns_peer[0])
        loginfo.log (netstring.encode (model))
        
if question[1] == 'PTR':
        question = (ip_peer.in_addr_arpa (question[0]), question[1])
dns_client.lookup (question, resolved, servers)
async_loop.dispatch ()
assert None == finalization.collect ()
sys.exit (0)