import time, subprocess

from allegra import loginfo, async_loop, finalization, synchronized

def test_producer (now, p, next_test):
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
                                async_loop.schedule (
                                        when + async_loop.async_timeout, 
                                        test_produce
                                        )
                        else:
                                async_loop.schedule (
                                        when + async_loop.async_timeout, 
                                        next_test
                                        )
                                
                
        async_loop.schedule (
                now + async_loop.async_timeout, test_produce
                )        

def test_file_collector (when):
        loginfo.log ('test File_collector')
        c = synchronized.File_collector ('test.txt')
        c.collect_incoming_data ('this is a test\n')
        c.collect_incoming_data ('this is a test\n')
        c.collect_incoming_data ('this is a test\n')
        c.found_terminator ()
        async_loop.schedule (
                when + async_loop.async_timeout, test_file_producer
                )
        
def test_file_producer (when):
        loginfo.log ('test File_producer')
        p = synchronized.File_producer ('test.txt')
        test_producer (when, p, test_popen_producer)
        
def test_popen_producer (when):
        loginfo.log ('test Popen_producer')
        p = synchronized.popen_producer (
                '/python24/python test/subproduce.py'
                )
        test_producer (when, p, test_popen_collector)

def test_popen_collector (when):
        loginfo.log ('test Popen_collector')
        c = synchronized.popen_collector (
                '/python24/python test/subcollect.py'
                )
        c.collect_incoming_data ('this is a test\n\n')
        c.found_terminator ()
        async_loop.schedule (
                when + async_loop.async_timeout, test_popen_reactor
                )
        
def test_popen_reactor (when):
        loginfo.log ('test Popen_reactor')
        r = synchronized.Popen_reactor (
                '/python24/python test/subcollect.py'
                )
        test_producer (when, r.spout, (lambda when: None))
        r.scin.collect_incoming_data ('this is a test\n\n')
        r.scin.found_terminator ()
                        
async_loop.schedule (
        time.time () + async_loop.async_timeout, test_file_collector
        )
async_loop.dispatch ()
finalization.collect ()