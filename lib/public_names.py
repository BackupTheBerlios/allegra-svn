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
        # try to decode the articulated public names, strip voids
        names = netunicode.decode (encoded, False)
        if not names:
                if encoded not in field:
                        # clean name new in this horizon
                        field.add (encoded)
                        return encoded
                        
                # Public Name in the field
                return u''

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
                
        return u'' # nothing valid to articulate


# two conveniences for caching the validity of unicode strings as Public Names

def valid_as (encoded, contexts, horizon):
        try:
                return contexts[encoded]
        
        except KeyError:
                u = unicode (encoded, 'UTF-8')
                field = set ()
                if u == valid (u, field, horizon):
                        contexts[encoded] == field
                        return field


def valid_in (encoded, contexts, horizon):
        try:
                return contexts[encoded]
        
        except KeyError:
                u = unicode (encoded, 'UTF-8')
                field = set ()
                if u == valids (u, field, horizon):
                        return field


