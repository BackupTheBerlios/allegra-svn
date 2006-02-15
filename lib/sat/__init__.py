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

"SAT languages packages"

import re

def articulators_re (articulators):
        return re.compile (
                '(?:^|\\s+)'
                '((?:%s))'
                '(?:$|\\s+)' % ')|(?:'.join (articulators)
                )

# English linguists have mercy! Here's a frenchspeaker coding ...
#
# To put it straight, I aggregated a bizarre english grammar, scraped
# from the web at various places teaching the language's basics. This
# is an empirical and practical stack of simple RE that make up a
# simplistic but effective natural language lexer.
#
# writing a natural language lexer as a stack of RE is both practical
# and effective: CPython's SRE library is compliant and fast, and a
# stack is one of the easiest programming pattern possible.
#
# yet the result are surprisingly good for such vocabulary and formal
# pattern articulation (punctuation, case, etc). with as little loss
# as possible a SAT lexer can produce very well-articulated Public
# Names, but only time and test will tell which RE stack will prevail
# or carve a contextual niche and which one will be abandonned.

RE_Public_Names = re.compile ('[0-9]+[:]([^\\s]+?),+')

ARTICULATE_ASCII_Head = (
        # Public Names (and any netstring encoded look-alike ...)
        RE_Public_Names,
        # Major punctuation
        re.compile ('[?!.](?:\\s+|$)'), # sentences
        re.compile ('[:;](?:\\s+)'),    # property(ies)
        re.compile ('[,](?:\\s+)'),     # enumeration
        # All brackets, flattened, plus the ' - ' common pattern
        re.compile ('[(]|[)]|[[]|[]]|{|}|\\s+-+\\s+'),
        # Double quotes and a common web separator
        re.compile ('["&|]'), 
        # Subordinating Conjunctions
        )

ARTICULATE_ASCII_Tail = (
        # Noun (Upper case, like "D.J. Bernstein" or "RDF")
        re.compile ('(?:^|\\s+)((?:[A-Z]+[^\\s]*?(?:\\s+|$))+)'),
        # Whitespaces
        re.compile ('\\s'), 
        # All sorts of hyphens 
        re.compile ("[/*+\\-#']")
        )

ARTICULATE = ARTICULATE_ASCII_Head + ARTICULATE_ASCII_Tail 

