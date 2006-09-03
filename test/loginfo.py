import sys
from allegra import loginfo

loginfo.log ('message')
loginfo.log ('message', 'info')
try:
        foobar
except:
        ctb = loginfo.traceback ()

logged = loginfo.Loginfo ()
logged.log ('message')
logged.log ('message', 'info')

loginfo.toggle ()
logged.log ('message')

logged.loginfo_toggle ()
logged.log ('message')

logged.loginfo_toggle ()
try:
        foobar
except:
        ctb = logged.loginfo_traceback ()

loginfo.toggle ()
logged.loginfo_logger = loginfo.Loginfo ()
logged.log ('message')
logged.log ('message', 'info')

loginfo.traceback_encode = loginfo.classic_traceback
try:
        foobar
except:
        ctb = loginfo.traceback ()
        
print 1234
loginfo.traceback_encode = loginfo.compact_traceback
foobar