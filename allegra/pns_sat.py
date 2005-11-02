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

from allegra.netstring import netstrings_encode, netstrings_decode
from allegra.pns_model import pns_name


# Articulators an whitespaces for the roman alphabet, ymmv :-)
#
# This is enough for a UTF-8 articulation (like an RSS titles).

SAT_SPLIT_UTF8 = (
        # punctuation
        '?!.', ':;', ',',
        # brackets
        '()[]{}',
        # double quotes and a common web separator
        '"|', 
        # whitespaces: CRLF, LF, TAB and whitespace
        '\n\r\t ', 
        # hyphens
        "/*+-_#'", 
        )

SAT_STRIP_UTF8 = '\r\n\t '

def pns_sat_utf8 (
        articulated, horizon,
        HORIZON=126, depth=0, articulators=SAT_SPLIT_UTF8
        ):
        while articulated.find (articulators[depth]) < 0:
                depth += 1
                if depth < len (articulators):
                        continue
                
                return articulated

        if depth+1 < len (articulators):
                names = []
                for name in articulated.split (articulators[depth]):
                        if name == '':
                                continue
                                
                        name = pns_sat_utf8 (
                                name, horizon, HORIZON, depth+1, articulators
                                ) 
                        if name != '':
                                names.append (name)
                                if len (horizon) > HORIZON:
                                        break
        else:
                names = articulated.split (articulators[depth])
        if len (names) > 1:
                name = pns_name (netstrings_encode (names), set ())
                if not name or name in horizon:
                        return ''
                        
                horizon.add (name)
                return name
                
        if len (names) > 0 and names[0]:
                horizon.add (names[0])
                return names[0]
                
        return ''
        
        
# Now the real thing: Simple Articulated Text
        
def sat_articulators_re (articulators):
        return re.compile (
                '(?:^|\\s+)'
                '(?:(?:%s))'
                '(?:$|\\s+)' % ')|(?:'.join (articulators)
                )

# English linguists have mercy! Here's a frenchspeaker coding ...

SAT_ARTICULATE_EN = (
        # punctuation
        re.compile ('[?!.](?:\\s+|$)'), # sentences
        re.compile ('[:;](?:\\s+)'),    # property(ies)
        re.compile ('[,](?:\\s+)'),     # enumeration
        # all brackets, flattened, plus the ' - ' common pattern
        re.compile ('[(]|[)]|[[]|[]]|{|}|\\s+-+\\s+'),
        # quotes and a common web separator
        re.compile ('["&|]'), 
        # The Verb is First: "to be" and "to have"
        sat_articulators_re ((
                'am', 'is', 'are', 'was', 'were',
                'have', 'has', 'had',
                )),
        # Subordinating Conjunctions
        sat_articulators_re ((
                'after', 'although', 'because', 'before', 
                'once', 'since', 'though', 'till', 'unless', 'until', 'when', 
                'whenever', 'where', 'whereas', 'wherever', 'while', 
                'as\\s+if', 'as\\s+long\\s+as', 'as\\s+though', 'as', 
                'even\\s+though', 'even\\s+if', 'if\\s+only', 'if', 
                'in\\s+order\\s+that', 'now\\s+that', 'so\\s+that', 'that', 
                'rather\\s+than', 'than', 
                )), 
        # Coordinating and Correlative Conjunctions
        sat_articulators_re ((
                'and', 'but', 'or', 'yet', 'for', 'nor', 'so',
                'both', 'not\\s+only', 'but\\s+also', 'either', 'neither', 
                'whether', 
                )), 
        # Prepositions: Locators in Time and Place
        sat_articulators_re ((
                'in', 'at', 'on', 'to',
                )),
        # Articles
        sat_articulators_re ((
                'a', 'an', 'the', 
                )),
        # Noun (Upper case, like "D.J. Bernstein" or "RDF")
        re.compile ('((?:[A-Z]+[^\\s]*?\\s+)+)')
        # whitespaces
        re.compile ('\\s'), 
        # all sorts of hyphens 
        re.compile ("[/*+\\-_#']") 
        )


def pns_sat_re (
        articulated, horizon,
        HORIZON=126, depth=0, 
        articulators=SAT_ARTICULATE_EN, 
        whitespaces=SAT_STRIP_UTF8
        ):
        while articulators[depth].search (articulated) == None:
                depth += 1
                if depth < len (articulators):
                        continue
                
                return articulated

        if depth+1 < len (articulators):
                names = []
                for text in articulators[depth].split (articulated):
                        if text.strip (whitespaces) == '':
                                continue
                                
                        name = pns_sat_re (
                                text, set (), HORIZON, depth+1, articulators
                                ) 
                        if name != '':
                                names.append (name)
                                if len (horizon) > HORIZON:
                                        break
                                        
        else:
                names = articulators[depth].split (articulated)
        if len (names) > 1:
                return pns_name (netstrings_encode (names), horizon)
                
        if len (names) > 0 and names[0]:
                return names[0]
                
        return ''
        
        
def pns_sat_chunk (
        articulated, horizon, chunks, 
        HORIZON=126, depth=0, 
        articulators=SAT_ARTICULATE_EN, CHUNK=507,
        whitespaces=SAT_STRIP_UTF8
        ):
        # move down the stack of regexp until ...
        while articulators[depth].search (articulated) == None:
                depth += 1
                if depth < len (articulators):
                        continue
                
                # ... the end.
                return articulated

        # ... until an articulation is found.
        if depth+1 < len (articulators):
                if len (articulated) > CHUNK:
                        for text in articulators[depth].split (articulated):
                                if text.strip (whitespaces) == '':
                                        continue
                                        
                                horizon.update (pns_sat_chunk (
                                        text, set (), chunks,
                                        HORIZON, depth+1, articulators, CHUNK
                                        ))
                        return horizon
                        
                horizon = horizon.copy ()
                chunks.append ((
                        pns_sat_re (
                                articulated, horizon,
                                HORIZON, depth, articulators,
                                ), articulated
                        ))
                return horizon
                
        names = articulators[depth].split (articulated)
        if len (names) > 1:
                name = pns_name (netstrings_encode (names), horizon)
                if name:
                        chunks.append ((name, articulated))
        elif len (names) > 0 and names[0]:
                chunks.append ((names[0], None))
        return horizon
        
        
# extract valid public names or netstrings from SAT.
        
NETSTRING_RE = re.compile ('[1-9][0-9]*:')

def pns_sat_names (articulated, chunks, whitespaces=SAT_STRIP_UTF8):
        text = ''
        while articulated:
                m = NETSTRING_RE.search (articulated)
                if m == None:
                        if text.strip (whitespaces):
                                text += articulated
                                return text
                                
                        return articulated
                        
                end = m.end () + int (m.group ()[:-1])
                if end < len (articulated) and articulated[end] == ',':
                        text += articulated[:m.start ()]
                        chunks.append ((articulated[m.end ():end], None))
                        articulated = articulated[end+1:]                              
                else:
                        text += articulated[:m.end ()]
                        articulated = articulated[m.end ():]
        return text
        
        
# The usual suspects for litteral web references

SAT_RE_WWW = re.compile (
        # a few web URIs
        '(?:(http://)([^ /]+)((?:/[^ /]+)*))|' 
        # any e-mail address
        '(?:([^\\s]+)@([^\\s]+))'
        # what else? 
        )
        
def pns_sat_articulate (
        articulated, horizon, chunks,
        expression=SAT_RE_WWW, 
        whitespaces=SAT_STRIP_UTF8, 
        articulators=SAT_ARTICULATE_EN, 
        HORIZON=126, # the defacto limit of 512 bytes datagrams for questions
        CHUNK=198 # 66*3, three lines of free text qualify for a chunk
        ):
        text = ''
        articulated = pns_sat_names (articulated, chunks)
        while articulated:
                m = expression.search (articulated)
                if m == None:
                        text += articulated
                        break
                        
                text += articulated[:m.start ()]
                names = [
                        n for n in m.groups () 
                        if n != None and n.strip (whitespaces)
                        ]
                if names:
                        name = pns_name (
                                netstrings_encode (names), horizon, HORIZON
                                )
                else:
                        name = pns_name (m.group (), horizon, HORIZON)
                if name:
                        chunks.append ((name, m.group ()))
                articulated = articulated[m.end ():]
        text = text.strip (whitespaces)
        if len (text) > CHUNK:
                pns_sat_chunk (
                        text, horizon, chunks, 
                        HORIZON, 0, articulators, CHUNK, whitespaces
                        )
        elif len (text) > 0:
                chunks.append ((pns_sat_re (
                        text, horizon, 
                        HORIZON, 0, articulators, whitespaces
                        ), text))
        
        
# TODO: a system pipe to articulate mime messages in pns_mime.py ;-)
        
# Note about this implementation
#
# Although "cheap", this is a multipurpose SAT articulator that will 
# fit many simple text articulations. As-is, it can articulate common
# UTF-8 text file, with an impressive depth. Not because it is complex,
# but because text *is* simply articulated ... and thanks to Larry's
# Perl Regular Expressions.
#
# How well text is articulated, that all depends first on the author.
#
# Public Names can preserve articulation, articulators should provide
# as much as practically possible.
#
# It's up to the user to articulate ideas, the computer can't.
#
# To infer semantic articulation to an unarticulated text is possible,
# and there are enough natural language toolkits that will do it a lot
# better than pns_sat.py. However, because articulators are specific
# and text is simply articulated, most applications of Public Names do
# not need much more than SAT to start with.
#
# Python comes with first-class PCRE support and this module implements
# a generic algorithm that articulates a text string against a stack
# of regular expressions.
#
# Each language should have its own stack. Dialects, jargons and protocols
# will have shorter stack than French or Japanese.
#
# Short formal text, like the RSS pubDate element or the HTML href attribute
# do not need a stack. A single regular expression that can yield a two level
# articulation is enough in most of those cases.
#

# The 8-bit byte string articulators and regular expressions provided are
# not applicable to all simple articulated text, but they will do nicely
# for most ASCII english web content out there. That's the biggest chunk
# available for large test purposes.
#
# The generic interface is this:
#
#        pns_sat (string, horizon, articulated=[], HORIZON=507)
#
# and fills a list with pairs:
#
#        [(public_name, articulated_text)]
#       
# This is practical to provide the accessor with the extracted regular
# expressions and chunks of natural language articulation separately, 
# ready for PNS statement.
#
#
# SAT for byte strings
#
#        horizon = set ()
#        name = pns_sat_utf8 ('This is a test.', horizon)
#
# Consume the string an build a public name until a given horizon from a 
# Simple Articulated Text encoded (SAT) in UTF-8 (or any other byte string).
#
# The first articulators are supposed to delimit less articulated text. 
# For instance a sentence delimited by a dot is usually more articulated than
# a sequence of words delimited by a coma, etc.
#
#
# SAT for web 
#
#        horizon = set ()
#        chunks = []
#        name = pns_sat_articulate (
#                'This is a test about laurentsyster.be. '
#                'e-mail: <contact@laurentszyster.be> '
#                'homepage: http://laurentszyster.be/blog/ ', 
#                horizon, chunks
#                )
#
# Use a regular expression to articulate a statement first around the 
# URI, e-mail, DNS domains and other computer references. Then SAT what
# is simple articulated text.
#