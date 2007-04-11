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

from allegra import presto

class Root (presto.Control):

        irtd2_timeout = 360 # Ten minute ... between actions
        
        root_password = 'presto'
        
        if __debug__:
                def new_password (self): pass
        else:
                def new_password (self): 
                        self.log (self.root_password, 'root')
                        self.root_password = presto.password ()
        
        def __init__ (self, peer, about):
                presto.Control.__init__ (self, peer, about)
                self.new_password ()

        def irtd2_unauthorized (self, reactor, about, json):
                if '4:root,' in reactor.irtd2[1]:
                        return False # authentic authorization found.
                
                # one time password check:
                if self.root_password == json.get (u"password"):
                        reactor.irtd2[1] += '4:root,' # add a role, ...
                        reactor.irtd2[4] = self.irtd2_salts[0] # salt and ...
                        presto.irtd2_authorize (
                                reactor, about, reactor.irtd2
                                ) # ... digest authentic authorizations.
                        self.new_password ()
                        return False # Authorized ?-)
                
                return True # Unauthorized !-(
                                
        def json_application (self, reactor, about, json):
                # check authorizations, maybe grant them ...
                if self.irtd2_unauthorized (reactor, about, json):
                        return reactor.http_produce (
                                401, presto.http_server.CONNECTION_CLOSE
                                ) # Unauthorized ... is a fatal HTTP error.
                                
                # dispatch the URL encoded form or JSON request ...
                if json.has_key (u"address"):
                        listen = presto.Listen.presto_root.get(
                                json[u"address"], (lambda x: None)
                                ) ()
                        if listen == None:
                                pass
                        elif json.has_key (u"load"):
                                listen.presto_load (json[u"load"])
                        elif json.has_key (u"unload"):
                                listen.presto_unload (json[u"unload"])
                return presto.json_200_ok (reactor, json)
        
if __debug__:
        controllers = {(u"127.0.0.2", u"root"): Root}
else:
        controllers = {(u"127.0.0.2", presto.password()): Root}
