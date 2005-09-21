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

# TODO: move to allegra/presto/127.0.0.1/pns_rss.py, this is an application
#
# It's both a system pipe available from a script and the component
# interface to manage it. Yet it runs completely independantly from PRESTo
# or PNS, with its own process and its own independant PNS/TCP connection.
#

from allegra import \
        netstring, xml_dom, xml_utf8, pns_model, pns_sat, pns_xml


class RSS_20_pubDate (pns_xml.XML_PNS_articulate):
        
        def xml_valid (self, dom):
                try:
                        daydatetime = self.xml_first.split (' ')
                        day = daydatetime[0].strip (',')
                        date = netstring.netstrings_encode (daydatetime[1:4])
                except:
                        pass
                else:
                        self.pns_object = ' '.join (daydatetime[:4])
                        self.pns_name = pns_model.pns_name (
                                netstring.netstrings_encode ((day, date))
                                )
                        self.xml_first = self.xml_children = None
                        

class DC_date (pns_xml.XML_PNS_articulate):
        
        def xml_valid (self, dom):
                if self.xml_parent ().xml_name != 'item':
                        return
                        
                try:
                        encoded = netstring.netstrings_encode (
                                self.xml_first.split (
                                        'T'
                                        )[0].split ('-')
                                )
                except:
                        pass
                else:
                        self.pns_name = pns_model.pns_name (encoded)
                        self.pns_object = self.xml_first
                        self.xml_first = self.xml_children = None
                        

RSS_DC_NAMESPACE = {
        # RSS 2.0 is real cool, simple *and* well articulated
        #
        'link': pns_xml.XML_PNS_name,
        'description': pns_xml.XML_PNS_validate,
        #
        # why not try other namespaces?
        #
        # http://purl.org/rss/1.0/ 
        #
        'http://purl.org/rss/1.0/ items': pns_xml.XML_PNS_orphan,
        'http://purl.org/rss/1.0/ link': pns_xml.XML_PNS_name,
        'http://purl.org/rss/1.0/modules/content/ encoded': \
                pns_xml.XML_PNS_validate,
        #
        # http://purl.org/dc/elements/1.1/
        #
        #'http://purl.org/dc/elements/1.1/ date': DC_date,
        }

#
# RDF, ATOM and others sucks way too much to bother for a test
# case ...
#
# Basically, most news aggregators support unprefixed RSS 2.0
# and the blogosphere is generating ad-hoc tags. Namespaces
# are only relevant to application developpers that have to
# aggregate. If you want all your ATOM semantics in PNS, feel
# free to implement your own articulator, I won't.
#

# TODO: an OPML_11 crawler for bulk import of a news reader
#       profile? move it to pns_opml.py and basta ...
        
class OPML_11_outline (pns_xml.XML_PNS_articulate):

        def xml_valid (self, dom):
                # name the outline from it's text attribute
                self.pns_object = self.xml_attributes.get ('text')
                self.pns_name = pns_sat.pns_sat_utf8 (self.pns_object)
                self.pns_articulate (self.pns_name, dom)
                
        def pns_xml_articulate (self, about, dom):
                # first, wget the xmlURL to ./pns_rss.tmp and articulate it
                if self.xml_attributes.get ('type') == 'rss':
                        os.system (
                                'wget.exe %s -q -Opns_rss.xml -T6'
                                '' % self.xml_attributes['xmlUrl']
                                )
                        rss_dom = pns_xml.PNS_XML_dom (
                                open ('pns_rss.xml', 'r'), dom.pns_name,
                                pns_xml.PNS_XML_element, PNS_RSS_NAMESPACE
                                )
                        dom.pns_name = rss_dom.pns_name
                # articulate simple XML for the OPML
                pns_xml.PNS_XML_element.pns_xml_articulate (self, about)
                # then dump the OPML snip and its SAT the description
                self.pns_xml_statement ((
                        about, 'XML', self.xml_string ()
                        ))
                description = self.xml_attributes.get ('description')
                if description:
                        self.pns_xml_statement ((
                                pns_sat_articulate (description),
                                'SAT',
                                description
                                ))


OPML_NAMESPACE = {
        'outline': OPML_11_outline,
        'head': pns_xml.XML_PNS_delete
        }


if __name__ == '__main__':
        import sys, time, os
        sys.stderr.write (
                'Allegra PNS/RSS'
                ' - Copyright 2005 Laurent A.V. Szyster'
                ' | Copyleft GPL 2.0\n'
                )
        # transform an XML string read from stdin into an PNS/TCP
        # session written to stdout
        #
        def pns_stdio_statement (statement):
                encoded = netstring.netstrings_encode (statement)
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
        dom.xml_class = pns_xml.XML_PNS_articulate
        dom.xml_classes = RSS_DC_NAMESPACE
        dom.xml_parser_reset ()
        dom.pns_statement = pns_stdio_statement
        dom.PNS_HORIZON = 126
        if len (sys.argv) > 1:
                devnull, stdin, stderr = os.popen3 (
                        'curl %s -q -H'
                        ' "Accept-Charset: utf-8, ascii-us;"' % sys.argv[1]
                        )
        else:
                stdin = sys.stdin
        dom.xml_parse_file (stdin)
        t = time.time () - t
        sys.stderr.write ('Transformed in %f secs\n' % t) 
        sys.exit ()


# Note about this implementation
#
# This is the first object-oriented XML validator built on the xml_dom.py
# interfaces. It enables simplicity of implementation when applied to
# semantic markup like HTML or RSS, with a short vocabulary and no DTD.
#
# The namespace implements the basic of RSS and OPML