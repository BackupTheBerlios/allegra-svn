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


import \
        sys, os, time, \
        win32serviceutil, win32service, win32event, win32process, \
        servicemanager


class Async_loop_win32 (win32serviceutil.ServiceFramework):

        _svc_name_ = 'Test'
        _svc_display_name_ = "Allegra (%s)" % _svc_name_
        
        process_min_time = 5
    
        def __init__ (self, args):
                win32serviceutil.ServiceFramework.__init__ (self, args)
                self.hWaitStop = win32event.CreateEvent (None, 0, 0, None)
    
        def SvcDoRun (self):
                self.start_process ()
                while 1:
                        rc = win32event.WaitForMultipleObjects (
                                (self.hWaitStop, self.hProcess), 
                                0, win32event.INFINITE
                                )
                        if rc - win32event.WAIT_OBJECT_0 == 0:
                                break
                        else:
                                self.restart_process ()
                self.ReportServiceStatus (
                        win32service.SERVICE_STOP_PENDING, 5000
                        )

        def SvcStop (self):
                servicemanager.LogInfoMsg ('stop') 
                try:
                        self.stop_process ()              
                except:
                        pass
                self.ReportServiceStatus (win32service.SERVICE_STOP_PENDING)
                win32event.SetEvent (self.hWaitStop)

        def start_process (self):
                sc = self.get_start_command ()
                result = win32process.CreateProcess (
                        None, self.get_start_command (),
                        None, None, 0, 0, None, None, 
                        win32process.STARTUPINFO ()
                        )
                self.hProcess = result[0]
                self.last_start_time = time.time ()
                servicemanager.LogInfoMsg ('start')
        
        def stop_process (self):
                win32process.TerminateProcess (self.hProcess, 0)
        
        def restart_process (self):
                if time.time() - self.last_start_time < self.process_min_time:
                        servicemanager.LogErrorMsg (
                                'died and could not be restarted.'
                                )
                        self.SvcStop ()
                code = win32process.GetExitCodeProcess (self.hProcess)
                if code == 0:
                        # Exited with a normal status code,
                        # assume that shutdown is intentional.
                        self.SvcStop ()
                else:
                        servicemanager.LogWarningMsg ('restart')
                        self.start_process ()

        def get_start_command(self):
                return win32serviceutil.GetServiceCustomOption (self, 'start')
        
        
def set_start_command(value):
        "sets the process start command, if not already set"
        current = win32serviceutil.GetServiceCustomOption (
                Async_loop_win32, 'start', None
                )
        if current == None:
                win32serviceutil.SetServiceCustomOption (
                        Async_loop_win32, 'start', value
                        )
            

if __name__ == '__main__':
        win32serviceutil.HandleCommandLine (Async_loop_win32)
        if 'install' in sys.argv:
                command = '"%s" "./presto_http.py"' % sys.executable
                set_start_command(command)
                print "Setting service command to:", command
                
                
# Note about this implementation
#
# This is the right way to do Win32 services: wrap a system command!
#
# TODO: drive this script at install time, but how to integrate with py2exe?
#