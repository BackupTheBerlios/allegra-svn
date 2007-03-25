# Copyright (C) 2007 Laurent A.V. Szyster
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
#    http://www.gnu.org/copyleft/gpl.html
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

import sys

from allegra import loginfo, async_loop, collector, pop_client

loginfo.log ('allegra/test/pop_client.py', 'info')
try:
    username = sys.argv[1]
    password = sys.argv[2]
    if len (sys.argv) > 3:
        host = sys.argv[3]
        if len (sys.argv) > 4:
            port = int (sys.argv[4])
            if len (sys.argv) > 5:
                order = sys.argv[5]
            else:
                order = None
        else:
            port = 110
    else:
        host = '127.0.0.1'
        port = 110
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

if __debug__:
    Collect = (lambda: collector.LOGINFO)
else:
    Collect = (lambda: collector.DEVNULL)
        
def capable ():
    if order == None and not (
        mailbox.pop_capabilities != None and
        'UIDL' in mailbox.pop_capabilities
        ):
        mailbox.pop_quit ()
    else:
        def authorized ():
            if order == None:
                mailbox.pop_uidl_and_retr (set (), Collect)
            else:
                mailbox.pop_retr_one (order, Collect)
                mailbox.pipeline_after_last (mailbox.pop_quit)
                    
        mailbox.pop_authorize (
            username, password, authorized, mailbox.pop_quit
            )
                
mailbox.pop_capable (capable)
async_loop.dispatch ()
sys.exit (0)