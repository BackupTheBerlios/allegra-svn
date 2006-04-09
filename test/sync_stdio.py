from allegra.async_loop import dispatch
from allegra.sync_stdio import Sync_stdoe, Python_prompt

Python_prompt ().start ()
dispatch ()
if __debug__:
    from allegra.finalization import collect
    collect ()
    
Sync_stdoe ().start ()
dispatch ()
if __debug__:
    from allegra.finalization import collect
    collect ()
    
    