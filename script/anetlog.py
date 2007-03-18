# Copyright (C) 2006 Laurent A.V. Szyster
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
#    http://www.gnu.org/copyleft/gpl.html
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

"http://laurentszyster.be/blog/anetlog/"

def main (
    root='./log', host='127.0.0.2', port=3998, 
    mkdir=False, mkclean=False, precision=3.0
    ):
    import os, stat
    from allegra import loginfo, async_loop, async_server
    loginfo.log (
        'anetlog'
        ' - Copyright 2006-2007 Laurent A.V. Szyster'
        ' | Copyleft GPL 2.0', 'info'
        )
    paths = ('tmp', 'new')
    for path in ('/'.join((root, p)) for p in paths):
        try:
            assert stat.S_ISDIR (os.stat (path)[0])
        except:
            if mkdir:
                os.makedirs (path)
            else:
                raise Exception (path + ' does not exist')
            
    if mkclean:
        import glob
        for path in ('/'.join((root, p, '*')) for p in paths):
            for fn in glob.glob(path):
                os.remove (fn)
    if hasattr (os, 'link'):
        _mode = 'w'
        _link = os.link
    elif os.name == 'nt':
        _mode = 'wb'
        import win32file
        def _link (from_name, to_name):
            win32file.CopyFileW (from_name, to_name, True)
            
    else:
        raise Exception ('os.link or equivalent interface not available')

    if __debug__:
        from allegra import netstring, async_net
        class Dispatcher (async_net.Dispatcher):
            def writable (self): 
                return False
            
            def async_net_continue (self, data):
                self.anetlog ('%d:%s,' % (len (data), data))
                loginfo.log (data, '%s:%d' % self.addr)

    else:
        from allegra import async_core
        class Dispatcher (async_core.Dispatcher):
            def writable (self):
                return False
            
            def handle_read (self): 
                self.anetlog (self.recv (16384))
            
    class Listen (async_server.Listen):
        def server_accept (self, conn, addr, name):
            dispatcher = async_server.Listen.server_accept (
                self, conn, addr, name
            )
            dispatcher.anetlog_name = filename = '%s_%f' % (
                '%s_%d' % dispatcher.addr, dispatcher.server_when
                )
            dispatcher.anetlog_file = file = open (
                '/'.join ((root, 'tmp', filename)), _mode
                )
            dispatcher.anetlog = file.write
            return dispatcher
      
        def server_close (self, dispatcher):
            async_server.Listen.server_close (self, dispatcher)
            dispatcher.anetlog_file.close ()
            _link (
                '/'.join ((root, 'tmp', dispatcher.anetlog_name)), 
                '/'.join ((root, 'new', dispatcher.anetlog_name))
                )
            
    async_loop.catch (
        Listen (Dispatcher, (host, port), precision, 5).server_shutdown
        )

      
if __name__ == '__main__':
    import sys
    from allegra import async_loop, finalization, anoption
    anoption.cli (main, sys.argv[1:])
    async_loop.dispatch ()
    assert None == finalization.collect ()        

# Note about this implementation
#
# This is a very simple netlog server that accept any connection,
# dump anything received in a new file, then close and link it from
# tmp/ into new/ when the socket is closed.
#
# Note that in debug mode it also prints out everything to STDOUT.
#
# It may block once in a while when writing to the file under high-load, 
# but the purpose here is not to respond to requests asap, it's an end point
# of contention ... out of its logging client, distributed on the network.
# Blocking at that point has little effect on the logging applications:
# the output queue of their netlog dispatcher will simply have to grow.
#
# You may prefer to apply tcpserver, djblibb and other fine software on
# POSIX systems, but such standards are not available for Windows. 