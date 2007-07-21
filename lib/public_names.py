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

"http://laurentszyster.be/blog/public_names/"

from allegra import netunicode


def valid (encoded, field, horizon):
        "validate encoded Public Names in a field and below a given horizon"
        # try to decode the articulated public names, strip voids
        names = tuple (netunicode.decode (encoded, False))
        if not names:
                # inarticulated names
                if encoded in field:
                        # allready in the field
                        return u""
                
                # new in this field
                field.add (encoded)
                return encoded
                        
        # articulated Public Names
        valids = []
        for name in names:
                # recursively validate each articulated name
                name = valid (name, field, horizon)
                if name:
                        valids.append (name)
                        if len (field) >= horizon:
                                break # but only under this horizon
                                
        if len (valids) > 1:
                # sort Public Names and encode
                valids.sort ()
                return netunicode.encode (valids)
                
        if len (valids) > 0:
                # return a "singleton"
                return valids[0]
                
        return u"" # nothing valid to articulate


# three conveniences for testing the validity of byte strings as Public Names

def valid_utf8 (encoded, horizon):
        u = unicode (encoded, 'UTF-8')
        field = set ()
        if u == valid (u, field, horizon):
                return True

        return False
        
def valid_as_utf8 (encoded, contexts, horizon):
        "hit the contexts cache or validate 8bit Public Names and cache"
        try:
                return (contexts[encoded] != None)
        
        except KeyError:
                u = unicode (encoded, 'UTF-8')
                field = set ()
                if u == valid (u, field, horizon):
                        contexts[encoded] == field
                        return True

                return False

def valid_in_utf8 (encoded, contexts, horizon):
        "hit the contexts cache or validate 8bit Public Names"
        try:
                return (contexts[encoded] != None)
        
        except KeyError:
                u = unicode (encoded, 'UTF-8')
                field = set ()
                if u == valid (u, field, horizon):
                        return True

                return False

# Note about this implementation
#
# The valid function is an obvious candidate for optimization in C. It has
# two loops and is recursive, making it quite CPU intensive. Thanks to the
# fast implementation of CPython it is practical *in* Python but given its
# simplicity there is no reason not to optimize it *for* Python.