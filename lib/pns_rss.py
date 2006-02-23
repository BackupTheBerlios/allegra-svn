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

from allegra import xml_dom, pns_xml


class RSS_channel (pns_xml.Articulate):
        
        xml_valid = pns_xml.xml_utf8_context


class RSS_title (pns_xml.Articulate):
        
        xml_valid = pns_xml.xml_utf8_name
        

class RSS_item (pns_xml.Articulate):
        
        xml_valid = pns_xml.xml_utf8_context
        
        def xml_valid (self, dom):
                pns_xml.xml_utf8_context (self, dom)
                xml_children = None
                #
                # remove articulated items from the parse tree


class RSS_pubDate (pns_xml.Articulate):
        
        pns_sat_language = (re.compile (
                '^(?:'
                '(?:([A-z]+?)[,]?\\s+)?' # day of the week Mon, Tue, ..., Sun. 
                '([0-3][0-9])\\s+([A-z]+)\\s+([0-9]{4})'# date 01 Jan 2001
                ')|' 
                '(?:'
                '\\s+([0-2][0-9]:[0-5][0-9]:[0-5][0-9])' # time 23:59:59
                '\\s+((?:GMT)|(?:[+\\-][0-9]{4}))' # and zone GMT or +0000
                ')?' 
                ),)

        def xml_valid (self, dom):
                pns_xml.xml_utf8_name (self, dom)
                self.pns_name = None        
                

markup = re.compile ('<.+?>')

class RSS_description (pns_xml.Articulate):
        
        def xml_valid (self, dom):
                # remove all markup from the description
                self.xml_first = ''.join (markup.split (self.xml_first))
                pns_xml.xml_utf8_chunk (self, dom)
                #
                # TODO: escape &#... to UTF-8 ?

                
RSS_TYPES = {
        # RSS 2.0 is real cool, simple *and* well articulated
        #
        'channel': RSS_channel,
        'title': RSS_title,
        'item': RSS_item,
        'pubDate': RSS_pubDate,
        'description': RSS_description,
        'link': pns_xml.Inarticulate,
        'guid': pns_xml.Inarticulate,
        #
        # http://purl.org/rss/1.0/ 
        #
        'http://purl.org/rss/1.0/ channel': RSS_channel,
        'http://purl.org/rss/1.0/ item': RSS_item,
        'http://purl.org/rss/1.0/ pubDate': RSS_pubDate,
        'http://purl.org/rss/1.0/modules/content/ encoded': RSS_description,
        #'http://purl.org/rss/1.0/ items': xml_dom.XML_delete,
        #'http://purl.org/rss/1.0/ image': ... rdf:resource
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


def rss_articulator (name, statement, dom=None):
        if dom == None:
                dom = xml_reactor.XML_collector (unicoding=0)
        dom.xml_type = xml_dom.XML_delete
        dom.xml_types = RSS_TYPES
        dom.pns_name = name
        dom.pns_statement = statement
        return dom

# The best part of it is that there is no need to declare DTD or worse
# to get the actual structure of the XML strings in a semantically
# undispersed graph, providing an interropperable namespace to application
# developpers. You can throw any XML at it, forget about database design
# headeaches: test the relevance of your existing information articulation,
# let it then evolve.

if __name__ == '__main__':
        import sys, time
        from allegra import async_loop, loginfo, http_client, xml_reactor
        assert None == loginfo.log (
                'Allegra PNS/RSS'
                ' - Copyright 2005 Laurent A.V. Szyster'
                ' | Copyleft GPL 2.0\n', 'info'
                )
        host, port, urlpath = re.compile (
                'http://([^/:]+)[:]?([0-9]+)?(/.+)'
                ).match (sys.argv[1]).groups ()
        t = time.clock ()
        if __debug__ or '-d' in sys.argv:
                dom = xml_reactor.XML_benchmark (unicoding=0)
        else:
                dom = xml_reactor.XML_collector (unicoding=0)
        pns_xml.articulate (
                dom, sys.argv[1], 'en', RSS_TYPES, xml_dom.XML_delete
                )
        http_client.GET (http_client.HTTP_client (
                ) (host, int (port or '80')), urlpath) (dom)
        async_loop.loop ()
        t = time.clock () - t
        if __debug__ or '-d' in sys.argv:
                loginfo.log (
                        'fetched in %f seconds, '
                        'as %d chunks parsed in %f seconds' % (
                                t, dom.xml_benchmark_count, 
                                dom.xml_benchmark_time
                                ), 'info'
                        )
        async_loop.dispatch ()