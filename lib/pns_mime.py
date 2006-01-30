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

SAT_RE = {
        'en': pns_sat.PNS_ARTICULATE_EN,
        'fr': pns_sat.PNS_ARTICULATE_FR,
        }

PLAIN_TEXT_RE = (
        re.compile ('\r?\n(?:\r?\n)+'), # paragraphs
        )

MIME_LANG = 'en'

class TEXT_PLAIN (object):
        
        mime_type = 'text/plain'
        
        collector_is_simple = True
        collector_stalled = False
        
        SAT_CHUNK = 507
        SAT_STRIP = pns_sat.SAT_STRIP_UTF8
        SAT_HORIZON = 126
        
        def __init__ (self, headers, articulators=None):
                self.articulators = PLAIN_TEXT_RE + (
                        articulators or SAT_RE[MIME_LANG]
                        )
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
                                pns_sat.pns_sat_chunk (
                                        more, 
                                        self.horizon, 
                                        self.articulated, 
                                        self.articulators,
                                        self.SAT_CHUNK, 
                                        self.SAT_STRIP, 
                                        self.SAT_HORIZON, 
                                        0
                                        )
        
        def find_terminator (self):
                if self.buffer:
                        pns_sat.pns_sat_chunk (
                                self.buffer, 
                                self.horizon, 
                                self.articulated, 
                                self.articulators,
                                self.SAT_CHUNK, 
                                self.SAT_STRIP, 
                                self.SAT_HORIZON, 
                                0
                                )


# Note about this implementation
# 
# This module implements a minimal MIME collector and UTF-8 transcoder 
# for PNS/SAT articulator, something practical to articulate plain text
# found in USENET and e-mail messages. However, its first test case is
# an HTTP/1.1 plain text indexer! There is a significant corpus of text
# in that format, for instance all the Internet's RFCs.
#
# 