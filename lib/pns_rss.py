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

from allegra import xml_dom, pns_sat, pns_xml, http_client, xml_reactor


markup = re.compile ('<.+?>')

class RSS_description (pns_xml.Articulate):
        
        def xml_valid (self, dom):
                # remove all markup from the description
                self.xml_first = ''.join (markup.split (self.xml_first))
                pns_xml.xml_utf8_chunk (self, dom)
                #
                # TODO: escape &#... to UTF-8 ?

                
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

        xml_valid = pns_xml.xml_utf8_sat


class RSS_language (pns_xml.Inarticulate):
        
        def xml_valid (self, dom):
                parent = self.xml_parent ()
                if parent.xml_name == 'channel':
                        dom.pns_sat_language = pns_sat.language (
                                self.xml_first
                                )

        #
        # the fact is that the <language/> element is stupidly placed, not
        # only *in* the item and channel but also *after* the title and 
        # description: errare humanum est, etc ...
        #
        # I mean there *is* a xml:lang attribute designed expressedly to
        # indicate the language for the content that follows!
        #
        # so here is the compromise: the <language/> effectively applies 
        # to the "default" language for the document articulated and
        # the item's language is ignored. 

        
class RSS_title (pns_xml.Articulate):
        
        def xml_valid (self, dom):
                # a <title/> names its parent, item or channel
                self.xml_parent ().pns_name = \
                        pns_xml.xml_utf8_sat (self, dom)
        

class RSS_category (pns_xml.Articulate):
        
        def xml_valid (self, dom):
                self.pns_name = pns_xml.xml_utf8_sat (self, dom)
        

class RSS_item (pns_xml.Articulate):
        
        xml_valid = pns_xml.xml_utf8_context


class RSS_channel (pns_xml.Articulate):
        
        def xml_valid (self, dom):
                # name the <rss/> root, at last and articulate the channel
                self.xml_parent ().pns_name = self.pns_name
                pns_xml.xml_utf8_context (self, dom)


class RSS_rss (pns_xml.Inarticulate):
        
        xml_valid = pns_xml.xml_utf8_root
        

RSS_TYPES = {
        # RDF's understanding of RSS is, after all, the less problematic 
        # protocol. At least it is flat and uses the xml:lang attribute.
        # The <channel/> element is obviously well placed but the sequence
        # of <items/> it contains is a clear redundancy (schmarkup to drop).
        #
        #'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
        #
        # Yet the most common is RSS 0.92 to 2.0
        #
        'link': pns_xml.Inarticulate,
        'guid': pns_xml.Inarticulate,
        'category': RSS_category,
        'pubDate': RSS_pubDate,
        'description': RSS_description,
        'title': RSS_title,
        'item': RSS_item,
        'channel': RSS_channel,
        'rss': RSS_rss,
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
        #'http://purl.org/dc/elements/1.1/ subject': RSS_category,
        #
        # ATOM is a big piece of s**t, much worse than RSS, verbose and
        # ill-articulated, with too many options bells and whistles, 
        # producing fat and deep document. Don't implement it. Please.
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
        }


def feed (url, statement, benchmark=True):
        host, port, urlpath = re.compile (
                'http://([^/:]+)[:]?([0-9]+)?(/.+)'
                ).match (url).groups ()
        if benchmark:
                dom = xml_reactor.XML_benchmark (unicoding=0)
        else:
                dom = xml_reactor.XML_collector (unicoding=0)
        pns_xml.articulate (
                dom, url, RSS_TYPES, xml_dom.XML_delete, statement
                )
        request = http_client.GET (http_client.HTTP_client (
                ) (host, int (port or '80')), urlpath) (dom)
        return dom, request


if __name__ == '__main__':
        import sys, time
        from allegra import async_loop, loginfo
        assert None == loginfo.log (
                'Allegra PNS/RSS'
                ' - Copyright 2005 Laurent A.V. Szyster'
                ' | Copyleft GPL 2.0\n', 'info'
                )
        t = time.clock ()
        dom, request = feed (
                sys.argv[1], 
                pns_xml.log_statement, 
                __debug__ or '-d' in sys.argv
                )
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