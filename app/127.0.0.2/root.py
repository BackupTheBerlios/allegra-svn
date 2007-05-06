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

from allegra import prompt, tcp_client, smtp_client, presto


def json_inspect (controller, reactor, about, json):
        response = {}
        response[u"method"], o = prompt.python_prompt (json.get(
                u"object", u"controller"
                ), {
                        'controller': controller, 
                        'reactor': reactor,
                        'about': about,
                        'json': json
                        })
        response[u"namespace"] = dir (o)
        if type (o) in presto.JSON_TYPES:
                response["value"] = presto.json_safe (o, set())
        else:
                if o != __builtins__ and hasattr(o, '__dict__'):
                        response[u"attributes"] = presto.json_safe (
                                o.__dict__, set()
                                )
        return response


class Root (presto.Control):

        irtd2_timeout = 360 # Ten minute ... between actions
        
        root_password = 'presto'
        smtp_relay = ('relay.chello.be', 25)

        def __init__ (self, peer, about):
                presto.Control.__init__ (self, peer, about)
                # self.new_password (about)

        def new_password (self, about): 
                mailto = smtp_client.Pipeline()
                if tcp_client.connect (mailto, self.smtp_relay):
                        def pipeline_close (reactor):
                                mailto.output_fifo.append ('QUIT\r\n')
                        mailto (
                                'root@127.0.0.2', 
                                ['contact@laurentszyster.be'],
                                self.http_uri + (
                                        '?root=%s' % self.root_password
                                        )
                                ).finalization = pipeline_close
        
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
                        # self.new_password (about)
                        return False # Authorized ?-)
                
                return True # Unauthorized !-(
        
        json_actions = {
                u"inspect": json_inspect,
                u"load": (
                        lambda json: 
                        presto.Listen.presto_root.get(
                                json.get (u"host", u"127.0.0.2")
                                ).presto_load (json[u"filename"])
                        ),
                u"unload": (
                        lambda json: 
                        presto.Listen.presto_root.get(
                                json.get (u"host", u"127.0.0.2")
                                ).presto_unload (json[u"filename"])
                        )
                }
                                
        def json_application (self, reactor, about, json):
                # check authorizations, maybe grant them ...
                if self.irtd2_unauthorized (reactor, about, json):
                        return reactor.http_produce (
                                401, presto.http_server.CONNECTION_CLOSE
                                ) # Unauthorized ... is a fatal HTTP error.
                                
                return presto.Control.json_application (
                        self, reactor, about, json
                        )
                

controllers = {(u"127.0.0.2", u"root"): Root}
