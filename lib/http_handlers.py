# Copyright (C) 2005 Laurent A.V. Szyster
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

def none (): pass

class File_cache (loginfo.Loginfo, finalization.Finalization):

        def __init__ (self, path): #, host):
                self.http_path = path
                # self.http_host = host
                self.http_cached = {}
                assert None == self.log (
                        'loaded path="%s"' % path, 'debug'
                        )
                
        def __repr__ (self):
                return 'http-cache path="%s"' % self.http_path
        
        def http_continue (self, reactor):
                if reactor.http_request[0] != 'GET':
                        reactor.http_response = 405 # Method Not Allowed 
                        return False
                        #
                        # TODO: add support for HEAD
                        
                filename = self.http_path + self.http_urlpath (reactor)
                teed = self.http_cached.get (filename, none) ()
                if teed != None:
                        reactor.producer_headers.update(teed.mime_headers)
                        reactor.producer_body = producer.Tee (teed)
                        reactor.http_response = 200
                        return False

                try:
                        result = os.stat (filename)
                except:
                        result = None
                if result == None or not stat.S_ISREG (result[0]):
                        reactor.http_response = 404
                        return False
                        
                teed = producer.File (open (filename, 'rb'))
                content_type, content_encoding = \
                        mimetypes.guess_type (filename)
                teed.mime_headers = {
                        'Last-Modified': (
                                time.asctime (time.gmtime (result[7])) + 
                                (' %d' % time.timezone)
                                ),
                        'Content-Type': content_type or 'text/html',
                        }
                if content_encoding:
                        teed.mime_headers['Content-Encoding'] = \
                                content_encoding
                reactor.producer_headers.update (teed.mime_headers)
                reactor.producer_body = producer.Tee (teed)
                reactor.http_response = 200
                self.http_cached[filename] = weakref.ref (teed)
                return False
        
        def http_urlpath (self, reactor):
                return urllib.unquote (reactor.http_uri[2])
        
        http_finalize = http_log

