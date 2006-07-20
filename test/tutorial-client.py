from allegra import (
    async_loop, finalization, async_chat, 
    async_limits, collector, async_client, 
    synchronized
    )

def test ():
        dispatcher = async_chat.Dispatcher ()
        if async_client.connect (
            dispatcher, ('66.249.91.99', 80), 3
            ):
            dispatcher. async_chat_push (
                "GET / HTTP/1.1\r\n"
                "host: 66.249.91.99\r\n"
                "Connection: close\r\n"
                "\r\n"
                )
            collector.bind_simple (
                dispatcher,
                synchronized.File_collector ('response.txt')
                )
            async_limits.limit_recv (
                dispatcher, 3, 1, (lambda: 1<<13)
                )
        dispatcher.finalization = (
            lambda finalized: 
                    finalized.log ('%r' % dir (finalized))
            )

if __name__ == '__main__':
        test ()
        async_loop.dispatch ()
        finalization.collect ()