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

from allegra import presto_bsddb

presto_components = (
        presto_bsddb.BSDDB_open,
        presto_bsddb.BSDDB_set,
        presto_bsddb.BSDDB_get,
        )

if __debug__:
        from allegra.presto_prompt import presto_debug_sync
        for component in presto_components:
                presto_debug_sync (component)

# This module can/should be used as a template for new synchronized components.