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

"The default PRESTo class available: a root interface"

import glob, os, stat, mimetypes

from xml_unicode import xml_attr
from allegra.presto import PRESTo_async, presto_xml


def presto_index (files):
        for filename, filestat in files:
                if stat.S_ISDIR (filestat[0]):
                        yield (
                                '<presto:directory name="%s"'
                                ' mime-type="%s" bytes="%d"'
                                ' />' % (
                                        xml_attr (filename), 
                                        mimetypes.guess_type (filename)[0],
                                        filestat[6]
                                        )
                                )
                        
                elif stat.S_ISREG (filestat[0]):
                        yield (
                                '<presto:file name="%s"'
                                ' mime-type="%s" bytes="%d"'
                                ' />' % (
                                        xml_attr (filename), 
                                        mimetypes.guess_type (filename)[0],
                                        filestat[6])
                                )
                                

class PRESTo_root (PRESTo_async):

        xml_name = u'http://presto/ root'
        
        def xml_valid (self, dom):
                self.xml_dom = dom # circle reference to "stick" on load

        presto_interfaces = set ((
                u'PRESTo', u'filename', u'static', u'dynamic'
                ))

        def presto (self, reactor):
                if not self.xml_children:
                        self.xml_children = [
                                self.presto_modules (reactor),
                                self.presto_dynamic (reactor),
                                self.presto_static (reactor),
                                ]
                else:
                        if reactor.presto_vector[u'dynamic']:
                                self.xml_children[1] = \
                                        self.presto_dynamic (reactor)
                        if reactor.presto_vector[u'static']:
                                self.xml_children[2] = \
                                        self.presto_static (reactor)

        def presto_root_load_module (self, reactor):
                filename = reactor.presto_vector.get (
                        u'filename'
                        ).encode ('ASCII', 'ignore').strip ()
                if filename and filename != 'root.py':
                        reactor.presto_root.presto_module_load (filename)
                if self.xml_children:
                        self.xml_children[0] = self.presto_modules (reactor)
                else:
                        self.presto (reactor)
                
        def presto_root_unload_module (self, reactor):
                filename = reactor.presto_vector.get (
                        u'filename'
                        ).encode ('ASCII', 'ignore').strip ()
                if filename and filename != 'root.py':
                        reactor.presto_root.presto_module_unload (filename)
                if self.xml_children:
                        self.xml_children[0] = self.presto_modules (reactor)
                else:
                        self.presto (reactor)
                
        def presto_modules (self, reactor):
                loaded = set ([
                        unicode (n, 'ASCII', 'ignore')
                        for n in reactor.presto_root.presto_modules.keys ()
                        ])
                available = set ([
                        unicode (n, 'ASCII', 'ignore')
                        for n in reactor.presto_root.presto_modules_dir ()
                        ]).difference (loaded)
                return ''.join ((
                        '<presto:modules xmlns:presto="http://presto/" >',
                        ''.join ([
                                '<presto:module loaded="yes" filename="%s" '
                                '/>' % xml_attr (n) for n in loaded
                                ]),
                        ''.join ([
                                '<presto:module loaded="no" filename="%s" '
                                '/>' % xml_attr (n) for n in available
                                ]),
                        '</presto:modules>'
                        ))
        
        def presto_dynamic (self, reactor):
                index_path = reactor.presto_vector[u'dynamic']
                dynamic = [
                        (os.path.basename (n), os.stat (n))
                        for n in glob.glob (u'./%s/%s*' % (
                                reactor.presto_root.http_path,
                                index_path
                                ))
                        ]
                return ''.join ((
                        '<presto:dynamic xmlns:presto="http://presto/"'
                        ' path="%s">' % xml_attr (index_path),
                        ''.join ([s for s in presto_index (dynamic)]),
                        '</presto:dynamic>'
                        ))

        def presto_static (self, reactor):
                index_host = os.path.basename (
                        reactor.presto_root.http_path
                        )
                index_path = reactor.presto_vector[u'static']
                static = [
                        (os.path.basename (n), os.stat (n))
                        for n in glob.glob (u'./http/%s/%s*' % (
                                index_host, index_path
                                ))
                        ]
                return ''.join ((
                        '<presto:static xmlns:presto="http://presto/"'
                        ' host="%s" path="%s">' % (
                                index_host, xml_attr (index_path)
                                ),
                        ''.join ([s for s in presto_index (static)]),
                        '</presto:static>'
                        ))

        presto_methods = {
                u'load': presto_root_load_module,
                u'unload': presto_root_unload_module,
                u'modules': presto_modules,
                u'dynamic': presto_dynamic,
                u'static': presto_static,
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