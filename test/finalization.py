import time, gc

from allegra import loginfo, async_loop, finalization


# boiler plate

def watch (finalized):
        "inspect the continuation"
        loginfo.log ('%r - %d: %r' % (
                finalized, 
                len (finalized.async_finalized), 
                finalized.async_finalized
                ))

class Labeled (finalization.Finalization):
        "labeled test finalization"
        def __init__ (self, label): self.label = label
        def __repr__ (self): return self.label
        
class Watch (Labeled):
        "log test continuation and inspect the continuation"
        def __call__ (self, finalized):
                loginfo.log ('%r continue %r - %d: %r' % (
                        self, finalized, 
                        len (finalized.async_finalized), 
                        finalized.async_finalized
                        ))

class Continue (Watch):
        
        label = 'Continue'
        
        def __init__ (self, finalizations):
                self.__call__, self.continued = finalization.continuation (
                        finalizations
                        )

class Join (Watch):
        
        label = 'Join'

        def __init__ (self, finalizations):
                self.finalizations = finalizations
        
        def __call__ (self, finalized):
                if self.finalizations:
                        for joined in self.finalizations:
                                joined.finalization = self
                        self.finalizations = None
                else:
                        watch (finalized)

# Test Syntax

def test_watch ():
        Watch ('A').finalization = Watch ('B')
        async_loop.dispatch ()

def test_continuation ():
        "test Continuation, Continue, Join and finalization"
        Continue ((
                Watch ('begin'),
                Watch ('one'),
                Join ((
                        Watch ('two'), 
                        Watch ('three')
                        )),
                Watch ('joined'),
                finalization.Branch ((
                        Watch ('end'), 
                        Watch ('branched'),
                        ))
                ))
        async_loop.dispatch ()


def test_cycle ():
        "test a finalizations' cycle collection"
        one = Watch ('one')
        two = Watch ('two')
        three = Watch ('three')
        four = Watch ('four')
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
                c.append (f)
                for j in range (N):
                        f.finalization = Finalization ()
                        f = f.finalization
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
        test_watch ()
        test_continuation ()
        test_cycle ()
        test_scale (10, 10, count=False)
        test_scale (100, 100, count=False)
        test_scale (1000, 1000, count=False)