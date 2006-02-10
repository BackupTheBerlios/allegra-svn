import time

from allegra import loginfo, async_loop, finalization


# boiler plate

def inspect (finalized):
        loginfo.log ('%r - %d: %r' % (
                finalized, 
                len (finalized.async_finalized), 
                finalized.async_finalized
                ))

class Finalization (finalization.Finalization):
        def __init__ (self, label): self.label = label
        def __repr__ (self): return self.label
        
class Continuation (Finalization):
        def __call__ (self, finalized):
                loginfo.log ('%r continue %r - %d: %r' % (
                        self, finalized, 
                        len (finalized.async_finalized), 
                        finalized.async_finalized
                        ))

# Tests

def test_continuation ():
        finalization.Continue ((
                Continuation ('begin'),
                finalization.Join ((
                        Continuation ('one'), 
                        Continuation ('two')
                        )),
                Continuation ('joined'),
                Continuation ('end')
                )).finalization = inspect
        async_loop.dispatch ()

def test_cycle ():
        one = Continuation ('one')
        two = Continuation ('two')
        three = Continuation ('three')
        four = Continuation ('four')
        finalization.continuation ([one, two, three, four])
        four.cycle = three
        del one, two, three, four
        async_loop.dispatch ()
        import gc
        gc.collect ()
        loginfo.log ('garbage: %r' % gc.garbage)

def test_scale (N, M, Finalization=finalization.Finalization, count=False):
        if count:
                Finalization.count = 0
                def finalize (finalization, finalized):
                        Finalization.count += 1
        else:
                finalize = lambda finalization, finalized: None
        Finalization.__call__ = finalize
        t = time.clock ()
        c = []
        for i in range (M):
                f = Finalization ()
                for j in range (N):
                        f.finalization = Finalization ()
                        f = f.finalization
                c.append (f)
        t = time.clock () - t
        loginfo.log ('%d instanciations: %f seconds' % (N*M, t))
        t = time.clock ()
        del c
        finalization.async_loop.dispatch ()
        t = time.clock () - t
        try:
                loginfo.log ('%d finalizations: %f seconds' % (
                        Finalization.count, t
                        ))
        except:
                loginfo.log ('finalization: %f seconds' % t)
                
if __name__ == '__main__':
        test_continuation ()
        test_cycle ()
        test_scale (10, 10, count=False)
        test_scale (100, 100, count=False)
        test_scale (1000, 1000, count=False)