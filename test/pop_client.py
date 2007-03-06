import sys

from allegra import loginfo, async_loop, collector, pop_client

loginfo.log ('allegra/test/pop_client.py', 'info')
try:
    username = sys.argv[1]
    password = sys.argv[2]
    if len (sys.argv) > 3:
        uid = sys.argv[3]
        if len (sys.argv) > 4:
            host = sys.argv[4]
            if len (sys.argv) > 5:
                port = int (sys.argv[5])
            else:
                port = 110
        else:
            host = '127.0.0.1'
            port = 110
    else:
        pass
except:
    loginfo.log (
        'Invalid arguments,'
        ' use: user pass [UID [host=127.0.0.1 [port=110]]]', 
        'fatal'
        )
    sys.exit (1)

mailbox = pop_client.connect (host, port)
if mailbox == None:
    loginfo (
        'TCP/IP failure,'
        ' check your network configuration', 
        'fatal'
        )
    sys.exit (2)
else:
    if __debug__:
        COLLECT = collector.LOGINFO
    else:
        COLLECT = collector.DEVNULL
    def capable ():
        if not (
            mailbox.pop_capabilities != None and
            'UIDL' in mailbox.pop_capabilities
            ):
            mailbox.pop_quit ()
        def authorized ():
            mailbox.pop_uidl_and_retr (uid, (lambda: COLLECT))
            mailbox.pop_quit_after_last ()
        mailbox.pop_authorize (
            username, password, authorized, mailbox.pop_quit
            )
    mailbox.pop_capable (capable)
async_loop.dispatch ()
sys.exit (0)