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

from allegra import presto, presto_http


def modules_index (component):
        root = component.xml_dom.presto_root
        loaded = set (root.presto_modules.keys ())
        available = set (root.presto_modules_dir ()).difference (loaded)
        return ''.join ((
                ''.join ((
                        '<presto:module loaded="yes" filename="%s" />' % n 
                        for n in loaded
                        )),
                ''.join ((
                        '<presto:module loaded="no" filename="%s" />' % n 
                        for n in available
                        )),
                ))


def module_load (component, reactor):
        ctb = component.xml_dom.presto_root.presto_module_load (
                reactor.presto_vector[u'filename'].encode (
                        'ASCII', 'ignore'
                        ).strip (' \t\r\n.') # no funky module path allowed!
                )
        component.xml_children[0] = modules_index (component)
        if ctb != None:
                return presto.presto_ctb (ctb)
                

def module_unload (component, reactor):
        component.xml_dom.presto_root.presto_module_unload (
                reactor.presto_vector[u'filename'].encode (
                        'ASCII', 'ignore'
                        ) # No need to check, we're unloading ;-)
                )
        component.xml_children[0] = modules_index (component)
        
        
class PRESTo_modules (presto.PRESTo_async):

        xml_name = u'http://presto/ modules'
        
        def xml_valid (self, dom):
                self.xml_dom = dom
                self.xml_children = [modules_index (self)]
                
        presto = presto_http.get_rest

        presto_interfaces = set ((u'PRESTo', u'filename', ))
        
        presto_methods = {
                u'load': module_load,
                u'unload': module_unload,
                }


presto_components = (PRESTo_modules, )

if __debug__:
        from allegra.presto_prompt import presto_debug_async
        presto_debug_async (PRESTo_modules)
        
# Synopsis
#
# REST/XSLT
#
# GET http://host/modules.xml 1.1
# GET http://host/modules.xml?PRESTo=load&filename=... 1.1
# GET http://host/modules.xml?PRESTo=unload&filename=... 1.1
