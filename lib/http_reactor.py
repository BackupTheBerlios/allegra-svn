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

""

from allegra import collector


# Simple transfert-encoding and content-encoding Producers

class Chunk_producer (object):

        "a producer for the 'chunked' transfer coding of HTTP/1.1."

        # Original comment of Sam Rushing
        #
        # "HTTP 1.1 emphasizes that an advertised Content-Length header MUST
        #  be correct.  In the face of Strange Files, it is conceivable that
        #  reading a 'file' may produce an amount of data not matching that
        #  reported by os.stat() [text/binary mode issues, perhaps the file is
        #  being appended to, etc..]  This makes the chunked encoding a True
        #  Blessing, and it really ought to be used even with normal files.
        #  How beautifully it blends with the concept of the producer."
        #
        # And how beautifully he implemented it!
        
        def __init__ (self, producer, footers=None):
                self.producer = producer
                if footers:
                        self.footers = '\r\n'.join (
                                ['0'] + footers
                                ) + '\r\n\r\n'
                else:
                        self.footers = '0\r\n\r\n'
                self.producer_stalled = self.producer.producer_stalled

        def more (self):
                if self.producer:
                        data = self.producer.more ()
                        if data:
                                return '%x\r\n%s\r\n' % (len (data), data)

                        self.producer = None
                        return self.footers
                        
                return ''


class Chunk_collector (object):

        "a wrapping collector for chunked transfer encoding"

        collector_is_simple = False
        
        chunk_extensions = None

        def __init__ (self, collector, set_terminator, headers=None):
                "insert a chunked collector between two MIME collectors"
                self.chunk_collector = collector
                self.set_terminator = set_terminator
                self.mime_collector_headers = headers or {}
                self.collect_incoming_data = self.chunk_collect_size
                self.chunk_size = ''
                self.chunk_trailers = None
                self.chunk_trailer = ''
                self.set_terminator ('\r\n')

        def chunk_collect_size (self, data):
                self.chunk_size += data

        def chunk_collect_trailers (self, data):
                self.chunk_trailer += data

        def found_terminator (self):
                if self.chunk_size == None:
                        # end of a chunk, get next chunk-size
                        self.set_terminator ('\r\n')
                        self.chunk_size = ''
                        self.collect_incoming_data = self.chunk_collect_size
                        return False # continue ...
                
                if self.chunk_size == '0':
                        # last chunk
                        if self.chunk_trailers == None:
                                self.chunk_trailers = []
                                self.collect_incoming_data = \
                                        self.chunk_collect_trailers
                                return False # continue ...
                        
                        elif self.chunk_trailer:
                                self.chunk_trailers.append (self.chunk_trailer)
                                self.chunk_trailer = ''
                                return False # continue ...
                        
                        elif self.chunk_trailers:
                                self.mime_collector_headers.update (
                                        mime_headers_map (self.chunk_trailers)
                                        )
                        self.chunk_collector.found_terminator ()
                        self.set_terminator ('\r\n\r\n') # ? check it out ?
                        del self.set_terminator
                        return True # final!

                # end of chunk size, collect the chunk with the wrapped 
                # collector
                #
                if self.chunk_size.find (';') > 0:
                        (
                                self.chunk_size, self.chunk_extensions
                                ) = self.chunk_size.split (';', 1)
                self.set_terminator (
                        int (self.chunk_size, 16) + 2
                        )
                self.chunk_size = None
                self.collect_incoming_data = \
                        self.chunk_collector.collect_incoming_data
                return False # continue ...


def http_collector_continue (reactor, collected):
        # decide wether and wich collector wrappers are needed
        if reactor.mime_collector_headers.get (
                'transfer-encoding', ''
                ).lower () == 'chunked':
                # HTTP/1.1 mostly
                if not collected.collector_is_simple:
                        collected = collector.Simple_collector (collected)
                reactor.mime_collector_body = Chunk_collector (
                        collected,
                        reactor.set_terminator,
                        reactor.mime_collector_headers
                        )
        else:
                # HTTP/1.0 mostly
                content_length = reactor.mime_collector_headers.get (
                        'content-length'
                        )
                if content_length:
                        if not collected.collector_is_simple:
                                collected = collector.Simple_collector (
                                        collected
                                        )
                        reactor.set_terminator (int (content_length))
                else:
                        reactor.set_terminator (None)
                reactor.mime_collector_body = collected

# TODO: charset and compression decoding.
#
# add charset decoding to UNICODE, with RFC-3023 and "bozo"
# detection a la UFP:
#
#        http://feedparser.org/docs/character-encoding.html
#
# and implement gzip, deflate, ...