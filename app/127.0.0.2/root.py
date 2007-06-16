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


def json_inspect (control, http, about, json):
        method, o = prompt.python_prompt (json.setdefault(
                u"object", u"control"
                ), {
                        'control': control, 
                        'http': http,
                        'about': about,
                        'json': json
                        })
        if (method == 'excp'):
                json[method] = presto.json_encode (o)
        else:
                if type (o) in presto.JSON_TYPES:
                        json[method] = presto.json_safe (o, set())
                elif o != __builtins__ and hasattr(o, '__dict__'):
                        json[u"properties"] = presto.json_safe (
                                o.__dict__, set()
                                )
                json[u"names"] = dir (o)
        return 200


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
                        def pipeline_close (smtp):
                                smtp.output_fifo.append ('QUIT\r\n')
                        mailto (
                                'contact@laurentszyster.be', 
                                ['laurentszyster@gmail.com'],
                                http.uri + '?root=%s' % self.root_password
                                ).finalization = pipeline_close
        
        def irtd2_unauthorized (self, http, about, json):
                if '4:root,' in http.irtd2[1]:
                        return False # authentic authorization found.
                
                # one time password check:
                if self.root_password == json.get (u"password"):
                        http.irtd2[1] += '4:root,' # add a role, ...
                        http.irtd2[4] = self.irtd2_salts[0] # salt and ...
                        presto.irtd2_identify (
                                http, about, http.irtd2
                                ) # ... digest authentic authorizations.
                        # self.new_password (about)
                        return False # Authorized ?-)
                
                return True # Unauthorized !-(
        
        json_actions = {
                u"inspect": json_inspect,
                u"load": (
                        lambda control, http, about, json: 
                        presto.Listen.presto_root.get(
                                json.get (u"host", u"127.0.0.2")
                                ).presto_load (json.get(u"filename"))
                        ),
                u"unload": (
                        lambda control, http, about, json: 
                        presto.Listen.presto_root.get(
                                json.get (u"host", u"127.0.0.2")
                                ).presto_unload (json.get(u"filename"))
                        )
                }
                                
        def json_application (self, http, about, json):
                # check authorizations, maybe grant them ...
                if self.irtd2_unauthorized (http, about, json):
                        # Unauthorized ... is a fatal HTTP error.
                        return http.error (401) 
                                
                return presto.Control.json_application (
                        self, http, about, json
                        )
                

controllers = {(u"127.0.0.2", u"root"): Root}
