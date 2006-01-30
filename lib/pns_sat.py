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

"PNS/SAT - Public Name System / Simple Articulated Text"

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

def pns_sat_utf8 (articulated, horizon, articulators, HORIZON, depth):
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
        

def articulate_utf8 (articulated, articulators=SAT_SPLIT_UTF8, HORIZON=126):
        horizon = set ()
        return (pns_sat_utf8 (
                articulated, horizon, articulators, HORIZON, 0
                ), horizon)
        
        
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

SAT_RE_Public_Names = re.compile ('[0-9]+[:]([^\\s]+?),+')

SAT_ARTICULATE_ASCII_Head = (
        # Public Names (and any netstring encoded look-alike ...)
        SAT_RE_Public_Names,
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

SAT_ARTICULATE_ASCII_Tail = (
        # Noun (Upper case, like "D.J. Bernstein" or "RDF")
        re.compile ('(?:^|\\s+)((?:[A-Z]+[^\\s]*?(?:\\s+|$))+)'),
        # Whitespaces
        re.compile ('\\s'), 
        # All sorts of hyphens 
        re.compile ("[/*+\\-_#']") 
        )


SAT_ARTICULATE_EN = SAT_ARTICULATE_ASCII_Head + (
        # Subordinating Conjunctions
        sat_articulators_re ((
                'after', 'although', 'because', 'before', 
                'once', 'since', 'though', 'till', 'unless', 'until', 'when', 
                'whenever', 'where', 'whereas', 'wherever', 'while', 
                'as', 'even', 'if', 'that', 'than',
                )), 
        # Coordinating and Correlative Conjunctions
        sat_articulators_re ((
                'and', 'or', 'not', 'but', 'yet', 
                'for', 'so', 
                'both', 'either', 'nor', 'neither', 'whether', 
                )), 
        # Prepositions: Locators in Time and Place
        sat_articulators_re ((
                'in', 'at', 'on', 'to',
                )),
        # Articles
        sat_articulators_re ((
                'a', 'an', 'the', 
                )),
        ) + SAT_ARTICULATE_ASCII_Tail


SAT_ARTICULATE_FR = SAT_ARTICULATE_ASCII_Head + (
        # Conjonctions de Subordination
        sat_articulators_re ((
                'comme', 'lorsque', 'puisque', 'quand', 'que', 'quoique', 'si'
                )),
        # Conjonctions de Coordination
        sat_articulators_re ((
                'mais', 'ou', 'et', 'donc', 'or', 'ni', 'car', 'cependant', 
                'n�anmoins', 'toutefois',
                )),
        # Pr�positions
        sat_articulators_re ((
                'devant', 'derri�re', 'apr�s', # le rang
                'dans', 'en', 'chez', 'sous', # le lieu
                'avant', 'apr�s', 'depuis', 'pendant', # le temps
                'avec', 'selon', 'de', # la mani�re
                'vu', 'envers', 'pour', '�', 'sans', 'sauf' # ? dispers�s
                )),
        # Articles
        sat_articulators_re ((
                'un', 'une', 'des', 'le', 'la', 'les', 'du', 
                'de\\s+la', "de\\+l'",
                ))
        ) + SAT_ARTICULATE_ASCII_Tail


# the SAT Regular Expression lexer itself ...

def pns_sat_re (
        articulated, horizon, articulators, 
        whitespaces=SAT_STRIP_UTF8, HORIZON=126, depth=0, 
        ):
        "Articulate text using a simple regular expression lexer"
        bottom = len (articulators)
        # move down the stack until an articulator pattern is matched ...
        while True:
                matched = articulators[depth].findall (articulated)
                if matched:
                        break

                depth += 1
                if depth == bottom:
                        # no match found, bottom of the stack reached.
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
                        if not text.strip (whitespaces):
                                continue
                                
                        name = pns_sat_re (
                                text, set (), articulators, 
                                whitespaces, HORIZON, depth+1 
                                ) 
                        if name:
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
        articulated, horizon, chunks, articulators,
        CHUNK, whitespaces, HORIZON, depth 
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
                                        text, set (), chunks, articulators, 
                                        CHUNK, whitespaces, HORIZON, depth+1
                                        ))
                        return horizon
                        
                # chunk no more, articulate ...
                name = pns_sat_re (
                        articulated, horizon, articulators, 
                        whitespaces, HORIZON, depth
                        )
                if name:
                        chunks.append ((name, articulated))
                return horizon
                
        # bottom of the stack reached, split ...
        names = [n for n in articulators[depth].split (articulated) if n]
        if len (names) > 1:
                name = pns_model.pns_name (netstring.encode (names), horizon)
                if name:
                        chunks.append ((name, articulated))
        elif names and names[0]:
                chunks.append ((names[0], None))
        return horizon
        

def articulate (
        articulated, articulators, 
        CHUNK=507, HORIZON=126, whitespaces=SAT_STRIP_UTF8
        ):
        chunks = []
        return (pns_sat_chunk (
                text, set (), chunks, articulators, 
                CHUNK, whitespaces, HORIZON, 0
                ), chunks)
        
# SYNOPSYS
#
# >>> from allegra import pns_sat
# >>> pns_sat.articulate_utf8 ('inarticulated')
# 'inarticulated'
# >>> horizon = set ()
# >>> pns_sat.articulate_utf8 ('articulated text', horizon)
# '11:articulated,4:text,', set ()
# >>> horizon
# set (['articulated', 'text'])
#
# >>> chunks = pns_sat.articulate_language (
#        pns_sat.SAT_RE_EN,
#        'Simply articulated english to test a Regular Expression lexer '
#        'for natural human language articulation. Note that it uses
#        'little punctuation and supports fairly complex articulations.', 
#        chunk=144
#        )
# >>> chunks[0]
# 
# >>> import netstring
# >>> print netstring.netlines (chunks[0][0])
#
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
#
# PNS/SAT is CPU intensive, actually it is quite slow in Python. Performances
# will improve as Public Names validation is optimized, yet the simplicity
# of the RE stack lexer and the process of articulation itself imply a high 
# profile. It is a fairly complex task, even if its implementation in Python
# appears so simple (but then that's more because of Python's elegance and
# its first class support for regular expression matching and simple text 
# processing).
#
# PNS/SAT articulator should therefore be threaded.