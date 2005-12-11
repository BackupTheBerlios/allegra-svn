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

from allegra import netstring, pns_model


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
        "a simplistic lexer for short UTF-8 text"
        bottom = len (articulators)
        while True:
                names = articulated.split (articulators[depth])
                if names:
                        break

                depth += 1
                if depth == bottom:
                        # not match found, bottom of the stack reached.
                        return articulated
                
        if depth + 1 < bottom:
                names = [pns_sat_utf8 (
                        name, horizon, HORIZON, depth+1, articulators
                        ) for name in names]
        h = set ()
        name = pns_model.pns_name (netstring.encode (names), h)
        if len (h) > 1:
                if name in horizon:
                        return ''
                        
                # articulated Public Names
                horizon.add (name)
                return name
                
        elif name:
                return name
                
        return ''
        
        
# Now the real thing: Simple Articulated Text
        
def sat_articulators_re (articulators):
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

SAT_ARTICULATE_EN = (
        # punctuation
        re.compile ('[?!.](?:\\s+|$)'), # sentences
        re.compile ('[:;](?:\\s+)'),    # property(ies)
        re.compile ('[,](?:\\s+)'),     # enumeration
        # all brackets, flattened, plus the ' - ' common pattern
        re.compile ('[(]|[)]|[[]|[]]|{|}|\\s+-+\\s+'),
        # quotes and a common web separator
        re.compile ('["&|]'), 
        # Subordinating Conjunctions
        sat_articulators_re ((
                'after', 'although', 'because', 'before', 
                'once', 'since', 'though', 'till', 'unless', 'until', 'when', 
                'whenever', 'where', 'whereas', 'wherever', 'while', 
                'as', 'even', 'if', 'that', 'than',
                )), 
        # Coordinating and Correlative Conjunctions
        sat_articulators_re ((
                'and', 'but', 'or', 'yet', 'for', 'nor', 'so',
                'both', 'not', 'but', 'either', 'neither', 
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
        re.compile ('(?:^|\\s+)((?:[A-Z]+[^\\s]*?(?:\\s+|$))+)'),
        # whitespaces
        re.compile ('\\s'), 
        # all sorts of hyphens 
        re.compile ("[/*+\\-_#']") 
        )


# the SAT Regular Expression lexer itself ...
#

def pns_sat_re (
        articulated, horizon,
        HORIZON=126, depth=0, 
        articulators=SAT_ARTICULATE_EN, 
        whitespaces=SAT_STRIP_UTF8
        ):
        # move down the stack until an articulator pattern is matched ...
        bottom = len (articulators)
        while True:
                matched = articulators[depth].findall (articulated)
                if matched:
                        break

                depth += 1
                if depth == bottom:
                        # not match found, bottom of the stack reached.
                        return articulated
                
        if type (matched[0]) == tuple:
                # validate "grouping" articulators as Public Names and add
                # them to the list of names articulated ...
                names = [
                        pns_model.pns_name (netstring.encode ([
                                s.strip (whitespaces) for s in groups
                                ]), horizon) for groups in matched
                        ]
        else:
                names = []
        if depth + 1 == bottom:
                # bottom of the stack reached, simply split
                names.extend (articulators[depth].split (articulated))
        else:
                # not yet at the bottom of the stack, recurse
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
                                                       
        # validate the articulated name(s) as a Public Names
        if len (names) > 1:
                return pns_model.pns_name (netstring.encode (names), horizon)
                
        if len (names) > 0 and names[0]:
                return names[0]
                
        return ''
        
                
# SAT chunking interface 
        
def pns_sat_chunk (
        articulated, horizon, chunks, 
        HORIZON=126, depth=0, 
        articulators=SAT_ARTICULATE_EN, CHUNK=507,
        whitespaces=SAT_STRIP_UTF8
        ):
        bottom = len (articulators)
        # move down the stack of regexp until ...
        while articulators[depth].search (articulated) == None:
                depth += 1
                if depth < bottom:
                        continue
                
                # ... the end.
                return articulated

        # ... an articulation is found.
        if depth + 1 < bottom:
                # not yet at the bottom of the stack, recurse ...
                if len (articulated) > CHUNK:
                        # chunk more ...
                        for text in articulators[depth].split (articulated):
                                if text.strip (whitespaces) == '':
                                        continue
                                        
                                horizon.update (pns_sat_chunk (
                                        text, set (), chunks,
                                        HORIZON, depth+1, articulators, CHUNK
                                        ))
                        return horizon
                        
                # chunk no more, articulate ...
                horizon = horizon.copy ()
                chunks.append ((
                        pns_sat_re (
                                articulated, horizon,
                                HORIZON, depth, articulators,
                                ), articulated
                        ))
                return horizon
                
        # bottom of the stack reached, split ...
        names = articulators[depth].split (articulated)
        if len (names) > 1:
                name = pns_model.pns_name (netstring.encode (names), horizon)
                if name:
                        chunks.append ((name, articulated))
        elif len (names) > 0 and names[0]:
                chunks.append ((names[0], None))
        return horizon
        
        
# cleasing out Public Names from SAT.
        
NETSTRING_RE = re.compile ('[1-9][0-9]*:')

def pns_sat_names (articulated, chunks, whitespaces=SAT_STRIP_UTF8):
        "extract valid public names or netstrings from SAT"
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
                        name = pns_model.pns_name (
                                netstring.encode (names), horizon, HORIZON
                                )
                else:
                        name = pns_model.pns_name (m.group (), horizon, HORIZON)
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
        
        
# TODO: a simplification of SAT, making it tolerant to Public Names and
#       netstrings (simply, validate them!) and "grouping" at inside
#       the regexp at the same level as the articulated parts, effectively
#       allowing to keep *and* rearticulate some of the patterns matched
#       with the rest of the stack beneath.
#
#       writing a natural language lexer as a stack of RE is both practical
#       and effective: CPython's SRE library is compliant and fast, and a
#       stack is one of the easiest programming pattern possible.
#
#       yet the result are surprisingly good for such vocabulary and formal
#       pattern articulation (punctuation, case, etc). with as little loss
#       as possible a SAT lexer can produce very well-articulated Public
#       Names, but only time and test will tell which RE stack will prevail
#       or carve a contextual niche and which will be abandonned.

# Note about this implementation
#
# What a PNS/SAT articulator does is "read" a text by chunks and produce
# for each chunk a sequence of statements:
#
#        3:The,11:articulated,5:first,4:text,
#        sat
#        The first articulated text
#
# to make in a context named after the chunk's semantic horizon.
