# Copyright (C) 2006 Laurent A.V. Szyster
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

"""<h3>Synopsis</h3>

<p>To to generates data for <code>test/ansqlite.py</code> in a folder 
<code>db</code>, execute the following:

<pre>python test/anslqlite_data.py db/</pre>

<p>The following files

<pre>db/m4create.in</pre>

<p>and</p>

    db/m4insert.in
    db/m4update.in
    db/m4select.in

<p>are filled with SQL statements about a Public RDF table.</p>

"""

import sys

from allegra import ansqlite

root = 'db/'
N = range (1000)
M = range (100)
try:
        root = sys.argv[1]
        N = range (int (sys.argv[2]))
        M = range (int (sys.argv[3]))
except:
        pass

f = open (root + 'm4create.in', 'wb')
ansqlite.encode (f.write, (
        "BEGIN;"
        "CREATE TABLE m4statements("
                "m4subject, m4predicate, m4object, m4context"
                ");"
        "CREATE INDEX m4routes ON m4statements(m4subject, m4context);"
        "CREATE INDEX m4contexts ON m4statements(m4context);"
        "COMMIT;",
        None
        ))
f.close ()

f = open (root + 'm4insert.in', 'wb')
for i in N:
        ansqlite.encode (f.write, (
                "INSERT INTO m4statements("
                        "m4subject, m4predicate, m4object, m4context"
                        ") values (?, ?, ?, ?)",
                tuple ((
                        (u"%d" % j, u"test", u"", u"%d" % i) for j in M
                        ))
                ))
ansqlite.encode (f.write, ("BEGIN; COMMIT;", None))
f.close ()

f = open (root + 'm4update.in', 'wb')
for i in N:
        ansqlite.encode (f.write, (
                "UPDATE m4statements "
                        "SET m4object = ? "
                        "WHERE m4subject = ? "
                                "AND m4context = ? "
                                "AND m4predicate = ?",
                tuple ((
                        (u"ok", u"%d" % j, u"test", u"%d" % i) for j in M
                        ))
                ))
        ansqlite.encode (f.write, ("BEGIN; COMMIT;", None))
f.close ()

f = open (root + 'm4selectM.in', 'wb')
for i in N:
        ansqlite.encode (f.write, (
                "SELECT "
                        "m4subject, m4predicate, m4object, m4context "
                "FROM m4statements "
                "WHERE m4context = ?", (u"%d" % i, )
                ))
f.close ()

f = open (root + 'm4select1.in', 'wb')
for i in N:
        ansqlite.encode (f.write, (
                "SELECT * FROM m4statements "
                "WHERE m4subject = ? AND m4context = ?", 
                (u"67", u"%d" % i)
                ))
f.close ()