import time

from allegra import loginfo, async_loop, synchronized

def test_collector (when):
        loginfo.log ('test File_collector')
        c = synchronized.File_collector ('test.txt')
        c.collect_incoming_data ('this is a test\n')
        c.collect_incoming_data ('this is a test\n')
        c.collect_incoming_data ('this is a test\n')
        c.found_terminator ()
        async_loop.schedule (
                when + async_loop.async_timeout, test_producer
                )
        
def test_producer (when):
        loginfo.log ('test File_producer')
        p = synchronized.File_producer ('test.txt')
        def test_produce (when):
                if p.producer_stalled ():
                        async_loop.schedule (
                                when + async_loop.async_timeout, 
                                test_produce
                                )
                else:
                        data = p.more ()
                        if data:
                                loginfo.log (data, 'p.more ()')
                        else:
                                async_loop.schedule (
                                        when + async_loop.async_timeout, 
                                        test_reactor
                                        )
                                
                
        async_loop.schedule (
                when + async_loop.async_timeout, test_produce
                )

def test_reactor (when):
        loginfo.log ('test Popen_reactor')
        
        
async_loop.schedule (
        time.time () + async_loop.async_timeout, test_collector
        )
async_loop.dispatch ()