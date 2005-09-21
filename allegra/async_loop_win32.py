# Copyright (C) 2005 Laurent A.V. Szyster
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

""

import threading, win32event

class Async_loop_thread (threading.Thread):

        def run (self):
                from allegra import loginfo, async_loop
                #
                # here wrap sys.stdout and sys.stdout and log to some
                # files or close both.
                #
                assert None == loginfo.log ('<async-loop/>', '')
                while (
                        async_loop.async_map and 
                        self.async_loop_continue ()
                        ):
                        try:
                                if async_loop.async_finalized:
                                        async_loop.async_immediate ()
                                if async_loop.async_defered:
                                        async_loop.async_clock ()
                                async_loop.async_poll (
                                        async_loop.async_timeout, 
                                        async_loop.async_map
                                        )
                        except async_loop.async_Exception:
                                break
                                        
                if async_loop.async_finalized:
                        assert None == self.log (
                                '<async-loop-finalize/>', ''
                                )
                        async_loop.async_immediate ()
                        

def SvcDoRun (self): # can I change that ugly name?
        event = threading.Event ()
        event.set ()
        service = Async_loop_thread ()
        service.async_loop_continue = event.isSet
        service.start ()
        win32event.WaitForSingleObject (
                self.hWaitStop, win32event.INFINITE 
                )
        event.clear ()
        service.join ()
