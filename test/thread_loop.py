# Direct Use

from allegra.thread_loop import Thread_loop

foobar = Thread_loop ()

from time import sleep

from allegra.async_loop import dispatch
from time import sleep
        
for i in range (4):
    foobar.thread_loop_queue ((
        sleep, (i, )
        ))
foobar.thread_loop_queue (None)
foobar.start ()
del foobar
dispatch ()

# Thread_loop inheritor

class Foobar (Thread_loop):
        
    def sleep (self, interval):
        sleep (interval)
        self.select_trigger_log (
            "sleeped %s s" % interval
            )
        
foobar = Foobar ()
for i in range (4):
    foobar.thread_loop_queue ((
        foobar.sleep, (i, )
        ))
foobar.thread_loop_queue (None)
foobar.start ()
del foobar
dispatch ()

# Synchronized finalization

from allegra.loginfo import log
from allegra.finalization import Finalization
from allegra.thread_loop import synchronized

class Foobar (Finalization):
        
    synchronizer = None
    synchronizer_size = 2
        
    __init__ = synchronized
        
    def sleep (self, interval):
        sleep (interval)
        self.select_trigger ((
            log, ("sleeped %s s" % interval, )
            ))
        
foobars = [Foobar () for j in range (4)]
for i in range (4):
    for foobar in foobars:
        foobar.synchronized ((
            foobar.sleep, (i, )
            ))
del foobar, foobars
dispatch ()
