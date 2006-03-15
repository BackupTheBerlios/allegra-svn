from time import sleep
from threading import Thread
from allegra.select_trigger import Select_trigger
        
class Foobar (Thread, Select_trigger):
    def __init__ (self, interval):
        self.interval = interval
        Select_trigger.__init__ (self)
        Thread.__init__ (self)
        self.start ()
        
    def run (self):
        self.select_trigger ((
            self.log, ("start", "debug")
            ))
        sleep (self.interval)
        self.select_trigger ((
            self.log, ("stop", "debug")
            ))
            
from allegra.async_loop import dispatch
[Foobar (x) for x in range (3)]
dispatch ()