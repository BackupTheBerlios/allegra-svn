# Copyright (C) 2007 Laurent A.V. Szyster
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

import sys, re, inspect

options = re.compile ("^--?([0-9A-Za-z]+?)(?:=(.+))?$")

def use (fun):
        named, collection, extension, defaults = inspect.getargspec (fun)
        O = len (defaults or ())
        M = len (named) - O
        mandatory = ', '.join (named[:M])
        if O > 0:
                optionals = ', '.join ((
                        "%s=%r" % (named[M+i], defaults[i]) 
                        for i in range (O)
                        ))
                if collection:
                        if M > 0:
                                return "%s [%s ...] [%s]" % (
                                        mandatory, named[-O-1], optionals
                                        )
                
                        return "[%s] [...]" % optionals

                if M > 0:
                        return "%s [%s]" % (mandatory, optionals)
        
                return "[%s]" % optionals
        
        if collection:
                if M > 0:
                        return "%s [%s ...] " % (mandatory, named[-O-1])
                
                return "[...]"

        return mandatory
        

def cli (fun, argv, err=(lambda msg: sys.stderr.write (msg+'\r\n') or False)):
        named, collection, extension, defaults = inspect.getargspec (fun)
        N = len (named)
        O = len (defaults or ())
        M = N - O
        mandatory = set (named[:M])
        names = set ()
        args = []
        kwargs = {}
        ordered = 0
        for value in argv:
                m = options.match (value)
                if m:
                        name, option = m.groups ()
                        if extension or name in mandatory:
                                if option == None:
                                        kwargs[name] = True
                                else:
                                        kwargs[name] = option
                elif ordered < N:
                        names.add (named[ordered])
                        if ordered > M:
                                value = type (defaults[ordered-M]) (value)
                        args.append (value) 
                        ordered += 1
                elif collection:
                        args.append (s)
                else:
                        return err ("too many arguments")
                        
        if len (args) < M:
                return err ("too few arguments")
                
        for i in range (1, N - ordered + 1):
                default = defaults[-i]
                name = named[-i]
                value = kwargs.get(name, default)
                try:
                        kwargs[name] = type (default) (value)
                except:
                        return err ("illegal argument: " + name)
                
        names.update (kwargs.keys ())
        if not mandatory.issubset (names):
                return err ("missing argument(s): " + ', '.join (
                        mandatory.difference (names)
                        ))
        
        return fun (*args, **kwargs)