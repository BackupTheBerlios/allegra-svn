import sys

from allegra import loginfo, async_loop, collector, pop_client

try:
        username = sys.argv[1]
        password = sys.argv[2]
        if len (sys.argv) > 3:
                host = sys.argv[3]
                if len (sys.argv) > 4:
                        port = int (sys.argv[4])
                else:
                        port = 110
        else:
                host = '127.0.0.1'
                port = 110
except:
        loginfo (
                'Invalid arguments,'
                ' use: user pass [host=127.0.0.1 [port=110]]', 
                'fatal'
                )
        sys.exit (1)

mailbox = pop_client.connect (host, port)
if mailbox == None:
        loginfo ('TCP/IP failure, check your network configuration', 'fatal')
        sys.exit (2)
else:
        mailbox.pop_capable ()
        def authorized ():
                mailbox.pop_uidl_and_retr ((lambda: collector.LOGINFO))
        mailbox.pop_authorize (username, password, authorized)
        mailbox.finalization = continue_pop_connection ()
async_loop.dispatch ()
sys.exit (0)