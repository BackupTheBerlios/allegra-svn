import time, subprocess

from allegra import loginfo, async_loop, finalization, synchronized

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
                                        test_popen_producer
                                        )
                                
                
        async_loop.schedule (
                when + async_loop.async_timeout, test_produce
                )
        

def test_popen_producer (when):
        loginfo.log ('test Popen_producer')
        p = synchronized.popen_producer (
                '/python24/python test/subproduce.py'
                )
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
                                        test_popen_collector
                                        )
                                
        async_loop.schedule (
                when + async_loop.async_timeout, test_produce
                )

def test_popen_collector (when):
        loginfo.log ('test Popen_collector')
        c = synchronized.popen_collector (
                '/python24/python test/subcollect.py'
                )
        c.collect_incoming_data ('this is a test\n\n')
        c.found_terminator ()
        
        
async_loop.schedule (
        time.time () + async_loop.async_timeout, test_file_collector
        )
async_loop.dispatch ()
finalization.collect ()