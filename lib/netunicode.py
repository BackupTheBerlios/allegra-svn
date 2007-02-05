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
#

"http://laurentszyster.be/blog/netunicode/"


def encode (unicodes):
        "encode an iteration of unicode strings as netunicodes"
        return u''.join ([u'%d:%s,' % (len (u), u) for u in unicodes])
        
                
def decode (buffer, nostrip=True):
        "iterate netunicodes in buffer, maybe strip void, trunk garbage"
        assert type (buffer) == unicode
        size = len (buffer)
        prev = 0
        while prev < size:
                pos = buffer.find (u':', prev)
                if pos < 1:
                        break
                        
                try:
                        next = pos + int (buffer[prev:pos]) + 1
                except:
                        break
        
                if next >= size:
                        break
                
                if buffer[next] == u',':
                        pos += 1
                        if nostrip or pos < next:
                                yield buffer[pos:next]

                else:
                        break
                        
                prev = next + 1


def validate (buffer, length):
        "iterate netunicodes, don't strip, keep garbage and fit to size"
        assert type (buffer) == unicode and length > 0
        size = len (buffer)
        prev = 0
        while prev < size and length:
                pos = buffer.find (u':', prev)
                if pos < 1:
                        if prev == 0:
                                raise StopIteration # not a netstring!
                        
                        break
                        
                try:
                        next = pos + int (buffer[prev:pos]) + 1
                except:
                        break
        
                if next >= size:
                        break
                
                if buffer[next] == u',':
                        length -= 1
                        yield buffer[pos+1:next]

                else:
                        break
                        
                prev = next + 1

        if length:
                length -= 1
                yield buffer[max (prev, pos+1):]
        
                while length:
                        length -= 1
                        yield u''
                        


def outline (encoded, format=u'%s\r\n', indent=u'  '):
        "recursively format nested netunicodes, by default as a CRLF outline"
        n = tuple (decode (encoded))
        if len (n) > 0:
                return u''.join ((outline (
                        e, indent + format, indent
                        ) for e in n))
                        
        return format % encoded


def netunicodes (instance):
        "encode a tree of instances as nested netunicodes"
        t = type (instance)
        if t == str:
                return instance
                
        if t in (tuple, list, set, frozenset):
                return encode ((netunicodes (i) for i in instance))
                
        if t == dict:
                return encode ((netunicodes (i) for i in instance.items ()))

        try:
                return u'%s' % instance
                
        except:
                return u'%r' % instance
                

def netlist (encoded):
        "return a list of strings or [encoded] if no netunicodes found"
        return list (decode (encoded)) or [encoded]


def nettree (encoded):
        "decode the nested netunicodes in a tree of lists"
        leaves = [nettree (s) for s in decode (encoded)]
        if len (leaves) > 0:
                return leaves
                
        return encoded


def netlines (encoded, format=u'%s\r\n', indent=u'  '):
        "beautify a netunicodes as an outline"
        n = tuple (decode (encoded))
        if len (n) > 0:
                return format % u''.join ((outline (
                        e, format, indent
                        ) for e in n))
                        
        return format % encoded


def netoutline (encoded, indent=u''):
        "recursively format nested netunicodes as an outline"
        n = tuple (decode (encoded))
        if len (n) > 0:
                return u'%s%d:\r\n%s%s,\r\n' % (
                        indent, len (encoded), u''.join ((netoutline (
                                e, indent + u'  '
                                ) for e in n)), indent)
        
        return u'%s%d:%s,\r\n' % (indent, len (encoded), encoded)
