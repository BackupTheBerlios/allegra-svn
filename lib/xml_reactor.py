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

import time

from xml.parsers import expat


from allegra import (
        finalization, async_chat, producer, collector, 
        xml_dom, xml_unicode, xml_utf8
        )


def xml_producer_unprefixed_utf8 (root, pi=None, globbing=512):
        head = '<?xml version="1.0" encoding="UTF-8"?>'
        if pi:
                head += xml_utf8.xml_pi (pi)
        return producer.Composite (
                head, xml_utf8.xml_unprefixed (root), globbing
                )
         

def xml_producer_utf8 (root, prefixes, pi=None, globbing=512):
        head = '<?xml version="1.0" encoding="UTF-8"?>'
        if pi:
                head += xml_utf8.xml_pi (pi)
        return producer.Composite (
                head, xml_utf8.xml_prefixed (
                        root, prefixes, xml_utf8.xml_ns (prefixes)
                        ), globbing
                )


def xml_producer_unprefixed_unicode (
        root, pi=None, encoding='ASCII', globbing=512
        ):
        head = '<?xml version="1.0" encoding="%s"?>' % encoding
        if pi:
                head += xml_unicode.xml_pi (pi, encoding)
        return producer.Composite (
                head, xml_unicode.xml_unprefixed (root, encoding), globbing
                )
         

def xml_producer_unicode (
        root, prefixes, pi=None, encoding='ASCII', globbing=512
        ):
        head = '<?xml version="1.0" encoding="%s"?>' % encoding
        if pi:
                head += xml_unicode.xml_pi (pi, encoding)
        return producer.Composite (
                head, xml_unicode.xml_prefixed (
                        root, prefixes, xml_unicode.xml_ns (prefixes), 
                        encoding
                        ), globbing
                )


class XML_collector (xml_dom.XML_dom, finalization.Finalization):
        
        collector_is_simple = True
        
        def __init__ (self, unicoding=1):
                if unicoding:
                        self.xml_prefixes = ({
                                u'http://www.w3.org/XML/1998/namespace': 
                                        u'xml'
                                        })
                else:
                        self.xml_prefixes = ({
                                'http://www.w3.org/XML/1998/namespace': 
                                        'xml'
                                        })
                self.xml_pi = {}
                self.xml_unicoding = unicoding
                self.xml_parser_reset ()

        def collect_incoming_data (self, data):
                if self.xml_error == None:
                        try:
                                self.xml_expat.Parse (data, 0)
                        except expat.ExpatError, error:
                                self.xml_expat_ERROR (error)
                                self.xml_expat = None

        def found_terminator (self):
                if self.xml_error == None:
                        try:
                                self.xml_expat.Parse ('', 1)
                        except expat.ExpatError, error:
                                self.xml_expat_ERROR (error)
                        self.xml_expat = None
                return True


class XML_benchmark (XML_collector):
        
        collector_is_simple = True
        
        xml_benchmark_time = xml_benchmark_count = 0
        
        def collect_incoming_data (self, data):
                self.xml_benchmark_count += 1
                if self.xml_error == None:
                        try:
                                t = time.clock ()
                                self.xml_expat.Parse (data, 0)
                                self.xml_benchmark_time += time.clock () - t
                        except expat.ExpatError, error:
                                self.xml_expat_ERROR (error)
                                self.xml_expat = None

        def found_terminator (self):
                if self.xml_error == None:
                        try:
                                t = time.clock ()
                                self.xml_expat.Parse ('', 1)
                                self.xml_benchmark_time += time.clock () - t
                        except expat.ExpatError, error:
                                self.xml_expat_ERROR (error)
                        self.xml_expat = None
                return True


class Dispatcher (async_chat.Dispatcher, xml_dom.XML_dom):
                
        def __init__ (
                self, xml_types,
                xml_type=xml_dom.XML_element, unicoding=0
                ):
                xml_dom.XML_dom.__init__ (self)
                self.xml_types = xml_types
                self.xml_type = xml_type
                self.xml_parser_reset (unicoding)
                async_chat.Dispatcher.__init__ (self)
        
        def __repr__ (self):
                return 'async-xml id="%x"' % id (self)

        def readable (self):
                return True

        def handle_read (self):
                "buffer more input and try to parse the XML stream"
                try:
                        self.xml_expat.Parse (
                                self.recv (self.ac_in_buffer_size), 0
                                )
                except expat.ExpatError, error:
                        self.xml_expat_ERROR (error)
                except:
                        self.handle_error ()


# Note about this implementation
#
# An XML collector and parser, bundled to the DOM, because flat
# is a better (and faster ;-) Python Zen. This collector might
# be wrapped with a chain of collectors, like for instance a Chunked
# Transfert Encoding collector wrapping a Simple collector that
# articulates a Multipart MIME collector which will instanciate
# this XML collector and maybe even wrap a charset decoder around 
# if it happens to provide transcoding to one of Expat's supported
# charsets.
#
# It may sound clumsy and slow at first (and specially the part
# about instanciation, which is not Python's forte), but think
# twice about memory consumption, CPU waisted on I/O wait state
# by synchronous processes, network *latency* and the requirement
# of *perceived* speed of a request/response cycle.
#
# But what if you have to:
#
# 1. Save the MIME Multipart envelope. Where? In memory? What if it
#    is big? The filesystem is not really an option. cStringIO?
#
# 2. Well, then you have to open that envelope once it completed
#    which may be a long time from now, while your program is
#    waisting all that buffer *and* CPU time!
#
# 3. And it is not finished, because you have to transcode and
#    parse it real fast now if you don't want to waiste your peer's
#    precious time, CPU resources and computer memory. Unfortunately
#    those are the most heavy processes, the slowest, the application
#    accessed itself.
#
# Instead, the XML_collector and possibly the charset transcoder
# may do that hard work as data is fetched from the network: slowly,
# each client beeing rationated via the size of its I/O buffer :-)
#
# This is very handy for ... entreprise network application
# interfaces, for computers that still don't know there is a
# network of peers out there and which produce batches. Mainframes
# and other big iron's applications are connected together by
# queues, can't export anything else than a batch. That translates
# into large XML interchanges with a practical request: get an
# acknowledgement ASAP for the whole batch.

                