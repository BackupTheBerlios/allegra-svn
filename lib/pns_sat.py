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


# Whitespaces for the roman alphabet, ymmv :-)

SAT_STRIP_UTF8 = ' \t\r\n'


# PNS/SAT languages - as named Stacks of Regular Expressions

LANGUAGES = {}

def language (name=None):
        "load a language module on demand and return its ARTICULATE stack"
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

def articulate_re (text, articulate, articulators, depth=0):
        "Articulate text using a simple regular expression lexer"
        bottom = len (articulators)
        # move down the stack until a pattern is matched ...
        while True:
                texts = [t for t in articulators[depth].split (text) if t]
                depth += 1
                if len (texts) > 1:
                        break

                if depth == bottom:
                        # no match found, bottom of the stack reached.
                        return text
                
        field = set ()
        if depth == bottom:
                # bottom of the stack reached, simply split
                name = pns_model.pns_name (netstring.encode (texts), field)
        else:
                # not yet at the bottom of the stack, recurse ...
                name = pns_model.pns_name (netstring.encode ((
                        articulate_re (
                                t, articulate, articulators, depth
                                ) for t in texts
                        )), field)
        # validate the articulated name(s) as a Public Names
        if len (field) > 1:
                articulate ((len (field), field, name, text))
        return name
        

def articulate_chunk (text, articulate, articulators, CHUNK, depth=0):
        "Articulate in chunks, usefull for larger text articulations"
        bottom = len (articulators)
        # move down the stack until a pattern is matched ...
        while True:
                texts = [t for t in articulators[depth].split (text) if t]
                depth += 1
                if len (texts) > 1:
                        break

                if depth == bottom:
                        # no match found, bottom of the stack reached, this
                        # is supposed to chunk, not articulate, do not name
                        # because it is inarticulated junk ...
                        return ''
                
        if depth == bottom:
                # bottom of the stack reached, simply split do not articulate
                # any further, there is nothing to chunk and it is a flat
                # articulation ...
                return pns_model.pns_name (netstring.encode ((
                        t for t in texts if len (t) <= CHUNK
                        )), set ())

        # not yet at the bottom of the stack, recurse
        for t in texts:
                if len (t) > CHUNK:
                        articulate_chunk (
                                t, articulate, articulators, CHUNK, depth, 
                                )
                else:
                        articulate_re (
                                t, articulate, articulators, depth
                                )
        return None


def articulate_languages (text, languages):
        "return the most articulated context and its language identifier"
        articulated_languages = []
        for lang in languages:
                articulated = []
                articulate_re (text, articulated.append, language (lang))
                articulated_languages.append ((
                        len (articulated), articulated, lang
                        ))
        articulated_languages.sort ()
        return articulated_languages[-1]


# Let's get a pure PNS/SAT dialog. Just this:
#
#  context\n
#  simple articulated text\n\n
#
# two fields, one for an articulated or inarticulated context (supposed to
# be a URI or any other computer reference ;-) and one for the simple
# articulated text of the PNS/SAT statement's subject(s).
#
# if no subject is provided, the context is searched for.
#
# It is a delicious blogpad.
