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

"A collection of functions to tokenize and parse MIME headers"

def lines (headers):
        l = ['%s: %s\r\n' % (n, v) for n,v in headers.items ()]
        l.append ('\r\n')
        return l


def split (string):
        "cleanse and split a string of MIME headers into lines"
        return string.replace ('\t', ' ').split ('\r\n')


def map (lines):
        "map a sequence of cleansed MIME header lines into a dictionnary"
        headers = {}
        n = None
        v = ''
        for line in lines:
                if 0 < line.find (':') < line.find (' '):
                        if headers.has_key (n):
                                try:
                                        headers[n].append (v)
                                except:
                                        headers[n] = [headers[n], v]
                        else:
                                headers[n] = v
                        n, v = line.split (':', 1)
                        n = n.strip ().lower ()
                        v = v.strip ()
                else:
                        v += line
        if headers.has_key (n):
                try:
                        headers[n].append (v)
                except:
                        headers[n] = [headers[n], v]
        else:
                headers[n] = v
        del headers[None] # remove collected garbage lines if any
        return headers
        
        
def options (headers, name):
        options = headers.get (name)
        if options == None:
                return (None, )
                
        return options.split (',')
        

def preferences (headers, name, default=None):
        options = headers.get (name)
        if options == None:
                return (default, )
                
        preferences = []
        for option in options.split (','):
                q = option.split (';')
                if len (q) == 2 and q[1].startswith ('q='):
                        preferences.append ((float (q[1][2:]), q[0]))
                else:
                        preferences.append ((1.0, q[0]))
        preferences.sort ()
        return [q[1] for q in preferences]
        

def value_and_parameters (line):
        """extract the tuple ('value', {'name'|0..n-1:'parameter'}) from a 
        MIME header line."""
        parameters = {}
        parts = [p.strip () for p in line.split (';')]
        for parameter in parts[1:]:
                if parameter.find ('=') > 0:
                        n, v = parameter.split ('=')
                        if v[0] == '"':
                                parameters[n] = v[1:-1]
                        else:
                                parameters[n] = v
                else:
                        parameters[len (parameters)] = v
        return parts[0], parameters

def get_parameter (line, name):
        "get the value of a parameter 'name' in a given header line"
        parts = [p.strip () for p in line.split (';')]
        for parameter in parts[1:]:
                if parameter.find ('=') > 0:
                        n, v = parameter.split ('=')
                        if n.lower () == name.lower ():
                                if v[0] == '"':
                                        return v[1:-1]
                                
                                else:
                                        return v
                                
        return None


# TODO: obvious candidate for C implementation