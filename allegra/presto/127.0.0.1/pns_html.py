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

# TODO: move to allegra/presto/127.0.0.1/pns_html.py, this is an application
#

XHTML_NAMESPACE = {
        'html': pns_xml.XML_PNS_articulate,
        'body': pns_xml.XML_PNS_articulate,
        'p': pns_xml.XML_PNS_articulate,
        'a': pns_xml.XML_PNS_articulate,
        'b': pns_xml.XML_PNS_articulate,
        'div': pns_xml.XML_PNS_orphan,
        'span': pns_xml.XML_PNS_orphan,
        'hr': pns_xml.XML_PNS_delete,
        'br': pns_xml.XML_PNS_delete,
        }


if __name__ == '__main__':
        import sys
        sys.stderr.write (
                'Allegra PNS/HTML Articulate!'
                ' - Copyright 2005 Laurent A.V. Szyster'
                ' | Copyleft GPL 2.0\n'
                )
        def pns_stdio_statement (statement):
                encoded = netstrings_encode (statement)
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
        
        import time, os , mimetypes
        t = time.time ()
        dom = xml_dom.XML_dom ()
        dom.xml_unicoding = 0 # UTF-8 only!
        dom.xml_class = xml_pns.XML_pns_drop
        dom.xml_classes = {}
        dom.xml_parser_reset ()
        dom.pns_statement = pns_stdio_statement
        dom.PNS_HORIZON = 126
        if len (sys.argv) > 1:
                dom.pns_context = sys.argv[1]
                devnull, stdin, stderr = os.popen3 ((
                        'curl %s -q'
                        ' -H "Accept-Charset: utf-8, ascii-us, iso-8859-1;"'
                        ' 2> curl.stderr'
                        ' | tidy -q -asxml 2> tidy.stderr' % about
                        ))
        else:
                dom.pns_context = 'test'
                stdin = sys.stdin
        dom.xml_parse_file (stdin)
        t = time.time () - t
        sys.stderr.write ('Transformed in %f secs\n' % t) 
        sys.exit ()