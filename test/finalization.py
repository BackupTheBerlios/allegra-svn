import time, gc

from allegra import loginfo, async_loop, finalization


# boiler plate

def inspect (finalized):
        "inspect the continuation"
        loginfo.log ('%r - %d: %r' % (
                finalized, 
                len (finalized.async_finalized), 
                finalized.async_finalized
                ))

class Finalization (finalization.Finalization):
        "labeled test finalization"
        def __init__ (self, label): self.label = label
        def __repr__ (self): return self.label
        
class Continuation (Finalization):
        "log test continuation and inspect the continuation"
        def __call__ (self, finalized):
                loginfo.log ('%r continue %r - %d: %r' % (
                        self, finalized, 
                        len (finalized.async_finalized), 
                        finalized.async_finalized
                        ))

# Test Syntax

def test_continuation ():
        "test Continuation, Continue, Join and finalization"
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
        "test a finalizations' cycle collection"
        one = Continuation ('one')
        two = Continuation ('two')
        three = Continuation ('three')
        four = Continuation ('four')
        finalization.continuation ([one, two, three, four])
        four.cycle = three
        del one, two, three, four
        async_loop.dispatch ()
        gc.collect ()
        loginfo.log ('garbage: %r' % gc.garbage)
        for cycled in gc.garbage:
                cycled.finalization = None
        async_loop.dispatch ()



def test_scale (N, M, Finalization=finalization.Finalization, count=False):
        "test scales on a system"
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