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

from allegra import netstring, pns_model, sat


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
        "/*+-#'", 
        )

SAT_STRIP_UTF8 = '\r\n\t '

def pns_sat_utf8 (articulated, field, articulators, HORIZON, depth):
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
                        name, field, HORIZON, depth+1, articulators
                        ) for name in names]
        f = set ()
        name = pns_model.pns_name (netstring.encode (names), f)
        if len (f) > 1:
                if name in field:
                        return ''
                        
                # articulated Public Names
                field.add (name)
                return name
                
        elif name:
                return name
                
        return ''
        

def articulate_utf8 (articulated, articulators=SAT_SPLIT_UTF8, HORIZON=126):
        field = set ()
        return (pns_sat_utf8 (
                articulated, field, articulators, HORIZON, 0
                ), field)
        
        
# Now the real thing: Simple Articulated Text
        
LANGUAGES = {}

def language (name):
        try:
                return LANGUAGES[name]
        except KeyError:
                try:
                        exec ('from allegra.sat import %s' % name)
                except:
                        articulator = LANGUAGES[name] = sat.ARTICULATE
                        #
                        # unknown languages should be articulated as ASCII
                        # using as much as possible of common punctuation and 
                        # capitalization for latin written languages.
                        #
                        # localized implementation may altern the default
                        # language by setting pns_sat.SAT_ARTICULATE to
                        # their alternative preference ...
                        #
                        # but failing is not an option!
                else:
                        articulator = LANGUAGES[name] = \
                                eval (name).ARTICULATE
                return articulator


# the SAT Regular Expression lexer itself ...

def pns_sat_re (
        articulated, field, articulators, whitespaces, HORIZON, depth
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
                                ]), field) for groups in matched
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
                                
                        f = set ()
                        name = pns_sat_re (
                                text, f, articulators, 
                                whitespaces, HORIZON, depth+1 
                                ) 
                        if name:
                                names.append (name)
                                if len (field) > HORIZON:
                                        break
                                
        # validate the articulated name(s) as a Public Names
        if len (names) > 1:
                return pns_model.pns_name (netstring.encode (names), field)
                
        if len (names) > 0 and names[0]:
                return names[0]
                
        return ''
        
                
# SAT chunking interface 
        
def pns_sat_chunk (
        articulated, field, chunks, articulators,
        CHUNK, whitespaces, HORIZON, depth 
        ):
        bottom = len (articulators)
        # move down the stack of regexp until ...
        while articulators[depth].search (articulated) == None:
                depth += 1
                if depth < bottom:
                        continue
                
                # ... the end.
                return field

        # ... an articulation is found.
        if depth + 1 < bottom:
                # not yet at the bottom of the stack, recurse ...
                if len (articulated) > CHUNK:
                        # chunk more ...
                        for text in articulators[depth].split (articulated):
                                if text.strip (whitespaces) == '':
                                        continue
                                        
                                field.update (pns_sat_chunk (
                                        text, set (), chunks, articulators, 
                                        CHUNK, whitespaces, HORIZON, depth+1
                                        ))
                        return field
                        
                # chunk no more, articulate ...
                name = pns_sat_re (
                        articulated, field, articulators, 
                        whitespaces, HORIZON, depth
                        )
                if name:
                        chunks.append ((name, articulated))
                return field
                
        # bottom of the stack reached, split ...
        names = [n for n in articulators[depth].split (articulated) if n]
        if len (names) > 1:
                name = pns_model.pns_name (netstring.encode (names), field)
                if name:
                        chunks.append ((name, articulated))
        elif names and names[0]:
                chunks.append ((names[0], None))
        return field
        

def articulate (
        articulated, articulators,
        CHUNK=504, # Seven lines of 72 characters
        HORIZON=126, # the PNS/Model limit for 1024 byte RDF statements
        whitespaces=SAT_STRIP_UTF8 # Strip UTF-8 whitespaces
        ):
        chunks = []
        field = set ()
        return (pns_sat_chunk (
                articulated, field, chunks, articulators, 
                CHUNK, whitespaces, HORIZON, 0
                ), chunks)
        
# SYNOPSYS
#
# >>> from allegra import pns_sat
# >>> pns_sat.articulate_utf8 ('inarticulated')
# 'inarticulated'
# >>> field = set ()
# >>> pns_sat.articulate_utf8 ('articulated text', field)
# '11:articulated,4:text,', set ()
# >>> field
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
# to make in a context named after the chunk's semantic field.
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