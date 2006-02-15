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

"SAT/EN - Simple Articulated Text / English"

from allegra import sat


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

ARTICULATE = sat.ARTICULATE_ASCII_Head + (
        # Subordinating Conjunctions
        sat.articulators_re ((
                'after', 'although', 'because', 'before', 
                'once', 'since', 'though', 'till', 'unless', 'until', 'when', 
                'whenever', 'where', 'whereas', 'wherever', 'while', 
                'as', 'even', 'if', 'that', 'than',
                )), 
        # Coordinating and Correlative Conjunctions
        sat.articulators_re ((
                'and', 'or', 'not', 'but', 'yet', 
                'for', 'so', 
                'both', 'either', 'nor', 'neither', 'whether', 
                )), 
        # Prepositions: Locators in Time and Place
        sat.articulators_re ((
                'in', 'at', 'on', 'to',
                )),
        # Articles
        sat.articulators_re ((
                'a', 'an', 'the', 
                )),
        ) + sat.ARTICULATE_ASCII_Tail
