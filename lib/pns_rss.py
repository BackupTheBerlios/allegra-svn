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

import re

from allegra import \
        netstring, xml_dom, xml_utf8, pns_model, pns_sat, pns_xml


class RSS_channel (pns_xml.XML_PNS_context):
        
        pns_articulated = set (('title', ))

        def xml_valid (self, dom):
                self.pns_articulate (
                        self.pns_subject, dom.pns_subject, dom
                        )
                xml_dom.xml_delete (self)

        
class RSS_item (pns_xml.XML_PNS_context):
        
        pns_articulated = set (('title', ))
        

class RSS_pubDate (pns_xml.XML_PNS_subject):
        
        SAT_RE = (re.compile (
                '^(?:'
                '(?:([A-z]+?)[,]?\\s+)?' # day of the week Mon, Tue, ..., Sun. 
                '([0-3][0-9])\\s+([A-z]+)\\s+([0-9]{4})'# date 01 Jan 2001
                ')|' 
                '(?:'
                '\\s+([0-2][0-9]:[0-5][0-9]:[0-5][0-9])' # time 23:59:59
                '\\s+((?:GMT)|(?:[+\\-][0-9]{4}))' # and zone GMT or +0000
                ')?' 
                ), )
        

RSS_NAMESPACE = {
        # RSS 2.0 is real cool, simple *and* well articulated
        #
        'channel': RSS_channel,
        'item': RSS_item,
        'pubDate': RSS_pubDate,
        'description': pns_xml.XML_PNS_enclosure,
        #
        # http://purl.org/rss/1.0/ 
        #
        'http://purl.org/rss/1.0/ channel': RSS_channel,
        'http://purl.org/rss/1.0/ item': RSS_item,
        'http://purl.org/rss/1.0/ pubDate': RSS_pubDate,
        'http://purl.org/rss/1.0/modules/content/ encoded': RSS_description,
        'http://purl.org/rss/1.0/ items': xml_dom.XML_delete,
        # 'http://purl.org/rss/1.0/ image': ... rdf:resource
        #
        # http://purl.org/dc/elements/1.1/
        #
        #'http://purl.org/dc/elements/1.1/ date': DC_date,
        #
        # ATOM
        #
        #'http://purl.org/atom/ns# feed'
        #'http://purl.org/atom/ns# entry'
        #'http://purl.org/atom/ns# link'
        #'http://purl.org/atom/ns# title'
        #'http://purl.org/atom/ns# tagline'
        #'http://purl.org/atom/ns# content'
        #'http://purl.org/atom/ns# info'
        #'http://purl.org/atom/ns# author'
        #'http://purl.org/atom/ns# modified'
        #'http://purl.org/atom/ns# created'
        #'http://purl.org/atom/ns# issued'
        #'http://purl.org/atom/ns# id'
        #
        # RDF's RSS
        #
        #'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
        #
        }

# The best part of it is that there is no need to declare DTD or worse
# to get the actual structure of the XML strings in a semantically
# undispersed graph, providing an interropperable namespace to application
# developpers. You can throw any XML at it, forget about database design
# headeaches: test the relevance of your existing information articulation,
# let it then evolve.

if __name__ == '__main__':
        import sys, time, os
        from allegra import loginfo
        assert None == loginfo.log (
                'Allegra PNS/RSS'
                ' - Copyright 2005 Laurent A.V. Szyster'
                ' | Copyleft GPL 2.0\n', 'info'
                )
        # transform an RSS document fetched from the network
        #
        def pns_stdio_statement (statement):
                encoded = netstring.encode (statement)
                if len (encoded) > 1024:
                        sys.stderr.write (
                                '%d:%s,' % (len (encoded), encoded)
                                )
                        return False
                        
                try:
                        sys.stdout.write (
                                '%d:%s,' % (len (encoded), encoded)
                                )
                except Exception, error:
                        sys.stderr.write ('Exception: %r\n' % error)
                        return False
                else:
                        return True
        
        t = time.time ()
        dom = xml_dom.XML_dom ()
        dom.xml_unicoding = 0 # UTF-8 only!
        dom.xml_type = pns_xml.XML_PNS_articulate
        dom.xml_types = RSS_NAMESPACE
        dom.xml_parser_reset ()
        dom.pns_statement = pns_stdio_statement
        dom.PNS_HORIZON = 126
        if len (sys.argv) > 1:
                dom.pns_subject = sys.argv[1]
                devnull, stdin, stderr = os.popen3 (
                        'curl %s -q -H'
                        ' "Accept-Charset: utf-8, ascii-us;"' % dom.pns_subject
                        )
        else:
                dom.pns_subject = '' # use xml:base?
                stdin = sys.stdin
        data = stdin.read (4096)
        while data:
                dom.xml_expat.Parse (stdin, 0)
        dom.xml_expat.Parse ('', 1)
        t = time.time () - t
        sys.stderr.write ('Transformed in %f secs\n' % t) 
        sys.exit ()
        