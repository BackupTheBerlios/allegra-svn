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

from allegra import loginfo, presto, ansqlite


class M4 (presto.Control):
        
        sql = None
        
        irtd2_timeout = 360 # Ten minute ... between actions
        
        def __init__ (self, peer, about):
                presto.Control.__init__ (self, peer, about)
                self.xml_root.xml_name = u"m4"
                self.sql_initialize ()
        
        def sql_initialize (self, finalized=None):
                self.sql = ansqlite.connect (
                        ('127.0.0.2', 3999), self.sql_initialize, 3.0
                        )
                self.sql (
                        self.sql_initialized,
                        "CREATE TABLE m4statements ("
                                "m4subject, m4predicate, m4object, m4context"
                                ");"
                        "CREATE INDEX m4routes ON m4statements ("
                                "m4subject, m4context"
                                ");"
                        "CREATE INDEX m4contexts ON m4statements (m4context);"
                        "CREATE TABLE m4index (m4names, m4index);",
                        None
                        )
                
        def sql_initialized (self, response):
                if response == None:
                        self.sql = None
        
        def m4_authorize (self, reactor, continuation):
                self.sql (
                        continuation,
                        "SELECT m4object FROM m4statements WHERE"
                                " m4predicate = 'password' AND"
                                " m4subject = ? AND"
                                " m4context = ?",
                        (reactor.irtd2[0], u"".join (reactor.uri_about[0]))
                        )
                        
        def json_application (self, reactor, about, json):
                # check authorizations, maybe grant them ...
                if reactor.irtd2[1].find ('4:root,') < 0:
                        return reactor.http_error (401) # ... or close!
                                
                return presto.json_200_ok (reactor, json)
        

controllers = {(u"127.0.0.2", u"m4"): M4}
