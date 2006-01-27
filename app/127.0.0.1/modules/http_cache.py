#  Copyright (C) 2005 Laurent A.V. Szyster
#
#  This library is free software; you can redistribute it and/or modify
#  it under the terms of version 2 of the GNU General Public License as
#  published by the Free Software Foundation.
#
#    http://www.gnu.org/copyleft/gpl.html
#
#  This library is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
#  You should have received a copy of the GNU General Public License
#  along with this library; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
#  USA

import os

from allegra import http_server, presto, presto_http


class PRESTo_http_cache (presto.PRESTo_async, http_server.HTTP_cache):
        
        xml_name = u'http://presto/ cache'
        
        __init__ = presto.PRESTo_async.__init__
        
        def xml_valid (self, dom):
                # get or set the cache's root path, but relatively to the 
                # PRESTo root, not absolutely.
                # 
                path = self.xml_attributes.setdefault (
                        u'root', u'/static'
                        ).encode ('UTF-8')
                # instanciate a new HTTP static file cache
                http_server.HTTP_cache.__init__ (
                        self, dom.presto_root.presto_path[:-5] + path
                        )
                # if a path was specified, move the cached weakref to it
                if path:
                        cached = dom.presto_root.presto_cached
                        path = path.encode ('UTF-8')
                        cached[path] = cached[dom.presto_path]
                        del cached[dom.presto_path]
                        dom.presto_path = path
                # cycle, effectively cache this instance
                self.xml_dom = dom
                        
        def http_urlpath (self, reactor):
                return reactor.presto_path[len (self.xml_dom.presto_path):]

        def presto (self, reactor):
                if reactor.presto_path != self.xml_dom.presto_path:
                        self.http_continue (reactor)
                else:
                        presto_http.get_method (self, reactor)

        presto_interfaces = set ()
        
        
if __debug__:
        from allegra.presto_prompt import presto_debug_async
        presto_debug_async (PRESTo_http_cache)

presto_components = (PRESTo_http_cache, )

        
# The <http-cache/> component is supposedly loaded to be 