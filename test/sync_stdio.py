from allegra import async_loop, sync_stdio

sync_stdio.Python_prompt ().start ()
async_loop.dispatch ()

sync_stdio.Sync_stdoe ().start ()
async_loop.dispatch ()

if __debug__:
        from allegra import finalization
        finalization.collect ()