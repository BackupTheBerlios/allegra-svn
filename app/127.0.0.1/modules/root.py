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

"The legacy PRESTo class available: a root interface"

import glob, os, stat, mimetypes

from allegra import xml_unicode, presto, presto_http


def filesystem_index (component, reactor):
        # browse a filesystem
        pass



class PRESTo_root (presto.PRESTo_async):

        xml_name = u'http://presto/ root'
        
        def xml_valid (self, dom):
                self.xml_dom = dom
                
        presto = presto_http.get_method

        presto_interfaces = set ((
                u'PRESTo', u'presto-host', u'presto-path',
                u'filename', u'static', u'dynamic'
                ))

        def presto_root (self, reactor):
                if not self.xml_children:
                        self.xml_children = [
                                self.presto_root_modules (reactor),
                                self.presto_root_dynamic (reactor),
                                ]

        def presto_root_load_module (self, reactor):
                filename = reactor.presto_vector.get (
                        u'filename'
                        ).encode ('ASCII', 'ignore').strip ()
                if filename and filename != 'root.py':
                        self.xml_dom.presto_root.presto_module_load (
                                filename
                                )
                if self.xml_children:
                        self.xml_children[0] = self.presto_root_modules (
                                reactor
                                )
                else:
                        self.presto (reactor)
                
        def presto_root_unload_module (self, reactor):
                filename = reactor.presto_vector.get (
                        u'filename'
                        ).encode ('ASCII', 'ignore').strip ()
                if filename and filename != 'root.py':
                        self.xml_dom.presto_root.presto_module_unload (
                                filename
                                )
                if self.xml_children:
                        self.xml_children[0] = self.presto_root_modules (
                                reactor
                                )
                else:
                        self.presto (reactor)
                
        def presto_root_modules (self, reactor):
                root = self.xml_dom.presto_root
                loaded = set ([
                        unicode (n, 'ASCII', 'ignore')
                        for n in root.presto_modules.keys ()
                        ])
                available = set ([
                        unicode (n, 'ASCII', 'ignore')
                        for n in root.presto_modules_dir ()
                        ]).difference (loaded)
                return ''.join ((
                        '<presto:modules xmlns:presto="http://presto/" >',
                        ''.join ([
                                '<presto:module loaded="yes" filename="%s" '
                                '/>' % xml_unicode.xml_attr (n) for n in loaded
                                ]),
                        ''.join ([
                                '<presto:module loaded="no" filename="%s" '
                                '/>' % xml_unicode.xml_attr (n) for n in available
                                ]),
                        '</presto:modules>'
                        ))
        
        def presto_root_dynamic (self, reactor):
                path = reactor.presto_vector[u'dynamic']
                dynamic = (
                        (os.path.basename (n), os.stat (n))
                        for n in glob.glob (u'%s/%s*' % (
                                self.xml_dom.presto_root.presto_path, path
                                ))
                        )
                return ''.join ((
                        '<presto:dynamic xmlns:presto="http://presto/"'
                        ' path="%s">' % xml_unicode.xml_attr (path),
                        ''.join ((s for s in presto_index (dynamic))),
                        '</presto:dynamic>'
                        ))

        presto_methods = {
                None: presto_root,
                u'load': presto_root_load_module,
                u'unload': presto_root_unload_module,
                u'modules': presto_root_modules,
                u'dynamic': presto_root_dynamic,
                }
                
                
if __debug__:
        from allegra.presto_prompt import presto_debug_async
        presto_debug_async (PRESTo_root)

presto_components = (PRESTo_root,)

# Note About this implementation
#
# This component is a good example of PRESTo component interface for
# an existing Python class (here allegra.presto.PRESTo_root).
#
#
# PRESTo's prompts
#
# By default the PRESTo async and sync prompt are not available and the
# debug prompt is available for the module loader instance only when the
# peer's Python interpreter itself whas started with the -OO flags.
#
# Basically, the default distribution of Allegra is for production
# deployement, not for a developpement install. And other modules should
# behave likewise, restricting access to debug console only when the peer
# itself is running in a debug mode. Allowing interactive development on
# a production site is a major security hole: eval() and exec() of arbitrary
# string is an exploit, and a serious one.