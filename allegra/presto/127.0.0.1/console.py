# Copyright (C) 2005 Laurent A.V. Szyster
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

""

from allegra.presto import PRESTo_sync

class Console (PRESTo_sync):
        xml_name = u'http://presto/ console'
        presto_interfaces = set ()
        presto_methods = {}

presto_components = (Console,)

if __debug__:
        from allegra.presto_prompt import presto_debug_sync
        presto_debug_sync (Console)

# This module can/should be used as a template for new synchronized components.