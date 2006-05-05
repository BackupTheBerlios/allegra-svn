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

from allegra import pns_sat

PLAIN_TEXT_RE = (re.compile ('\r?\n(?:\r?\n)+'), ) # paragraphs


class Collector (object):
        
        mime_type = 'text/plain'
        
        collector_is_simple = True
        collector_stalled = False
        
        def __init__ (self, headers, lang='en'):
                self.articulators = PLAIN_TEXT_RE + lang
                self.buffer = ''
                self.horizon = set ()
                self.articulated = []
        
        def collect_incoming_data (self, data):
                self.buffer += data
                match = self.articulators[0].search (self.buffer)
                if match:
                        next = match.start ()
                        if next > 0:
                                more = self.buffer[:next]
                                self.buffer = self.buffer[next:]
                                # ...
        
        def find_terminator (self):
                if self.buffer:
                        pass # ...


def articulate_headers (
        headers, context, statement, lang,
        names=('subject', ), predicates=('from', 'to', 'date', )
        ):
        articulated = []
        subject = pns_model.pns_name (netstring.encode ((
                pns_sat.articulate_re (
                        headers.get (n), articulated.append, lang
                        ) for n in names
                )))
        for predicate in predicates:
                object = headers.get (predicate)
                if object == None:
                        continue
                
                statement ((subject, predicate, object), )

# Note about this implementation
# 
# This module implements a minimal MIME collector and UTF-8 transcoder 
# for PNS/SAT articulator, something practical to articulate plain text
# found in USENET and e-mail messages. 
#
# The purpose of pns_mime is to support the Enron mail and comp.lang.python
# test cases, indexing all mail made available by the famous case and
# do the same for as much as comp.lang.python is available on USENET.
#
# The CLI is a pipe that collects a stream of MIME messages from STDIN and 
# pipes out articulated PNS statements on STDOUT:
#
#   pns_mime < mime 1> pns
#
# or if provided the proper arguments:
#
#   pns_mime 127.0.0.1 3534 < mime
#
# to a PNS/TCP metabase.

# <mime>
#   <id/>
#   <subject/>
#   <from/>
#   <to/>
#   <content-type/>
# </mime>
#