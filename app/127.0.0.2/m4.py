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

from allegra import presto, ansqlite


class M4 (presto.Control):
        
        irtd2_timeout = 360 # Ten minute ... between actions
        
        def __init__ (self, peer, about):
                presto.Control.__init__ (self, peer, about)
                self.xml_root.xml_name = u"m4"
                self.sql = ansqlite.connect (('127.0.0.2', 3999))
                self.sql (
                        'create if not exist table M4 ('
                        '...' # TODO: paste the SQL declaration
                        ');'
                        )
                        
        def m4_authorize (self, reactor, about):
                def continuation (response):
                        if response == None:
                                reactor.http_error (401)
                                
                        presto.xml_200_ok (reactor, self)
                        
                self.sql (
                        continuation,
                        'SELECT m4.object FROM m4 WHERE'
                        ' m4.predicate=password AND'
                        ' m4.subject=? AND'
                        ' m4.context=?',
                        (reactor.irdt2[0], u"".join (reactor.uri_about[0]))
                        )
                
        def http_resource (self, reactor, about):
                if about != reactor.uri_about:
                        if reactor.irtd2[1].find ('4:root,') < 0:
                                return presto.rest_302_redirect (
                                        reactor, about
                                        )
                
                        return reactor.http_produce (
                                200, 
                                
                                )
                
                return presto.xml_200_ok (reactor, self)
                                
        def json_application (self, reactor, about, json):
                # check authorizations, maybe grant them ...
                if reactor.irtd2[1].find ('4:root,') < 0:
                        return reactor.http_error (401) # ... or close!
                                
                return presto.json_200_ok (reactor, json)
        

controllers = {(u"127.0.0.2", u"m4"): M4}
