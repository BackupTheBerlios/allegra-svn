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

import os
from bsddb import db

from allegra import xml_utf8, xml_unicode
from allegra.presto import PRESTo_sync, presto_synchronize, presto_xml


class BSDDB_table:
        
        BSDDB_DB_TYPES = {
                u'BTREE': db.DB_BTREE,
                u'HASH': db.DB_HASH,
                u'RECNO': db.DB_RECNO,
                }
        BSDDB_DB_TYPE = db.DB_HASH
        BSDDB_OPEN_FLAGS = db.DB_THREAD # TODO: check if that can be relaxed

        bsddb_DB = None

        def bsddb_open (self, reactor):
                self.bsddb_DB = db.DB ()
                try:
                        self.bsddb_DB.open (
                                reactor.presto_vector[u'database'].encode (
                                        'ASCII', 'replace'
                                        ) +
                                os.path.sep +
                                reactor.presto_vector[u'name'].encode (
                                        'ASCII', 'replace'
                                        ),
                                dbtype=self.BSDDB_DB_TYPES.get (
                                        reactor.presto_vector[u'type'],
                                        self.BSDDB_DB_TYPE
                                        ),
                                flags=self.BSDDB_OPEN_FLAGS
                                )
                except db.DBError, excp:
                        return self.bsddb_open_exception (reactor, excp)
                        
                else:
                        return True
                        
        def bsddb_open_exception (self, reactor, excp):
                reactor ('<excp><![CDATA[%s]]></excp>' % excp)
                return False


class BSDDB_open (BSDDB_table, PRESTo_sync):
        
        # Simply creates a new bsddb table or an old oneif it exists
        # and reports its status or an error condition. This object
        # may be completely transient and used as a single interface
        # to create many database tables of different types, or to check
        # their status.
        
        xml_name = u'http://presto/ bsddb-open'
        xml_dom = None

        presto_interfaces = set ((u'PRESTo', u'name', u'type'))
        
        BSDDB_OPEN_FLAGS = (
                db.DB_CREATE | db.DB_EXCL | db.DB_THREAD
                )

        def bsddb_open_exception (self, reactor, excp):
                reactor ('<excp><![CDATA[%s]]></excp>' % excp)
                self.bsddb_DB = db.DB ()
                try:
                        self.bsddb_DB.open (
                                reactor.presto_vector[u'database'].encode (
                                        'ASCII', 'replace'
                                        ) + 
                                os.path.sep +
                                reactor.presto_vector[u'name'].encode (
                                        'ASCII', 'replace'
                                        ),
                                dbtype=db.DB_UNKNOWN,
                                flags=(db.DB_RDONLY | db.DB_THREAD)
                                )
                except db.DBError, excp:
                        BSDDB_table.bsddb_open_exception (self, reactor, excp)
                        return False
                        
                else:
                        return True

        def bsddb_open_presto (self, reactor):
                reactor ('<bsddb xmlns="http://presto/">')
                if self.bsddb_DB == None and not self.bsddb_open (reactor):
                        reactor ('</bsddb>')
                        reactor ('')
                        return
                        
                reactor ('<stat>%s</stat>' % presto_xml (
                                self.bsddb_DB.stat (), set ()
                                ))
                if self.xml_dom == None:
                        self.bsddb_DB.close ()
                        self.bsddb_DB = None
                reactor ('</bsddb>')
                reactor ('')
                
        presto_methods = {
                u'open': presto_synchronize ('bsddb_open_presto')
                }


class BSDDB_get (BSDDB_table, PRESTo_sync):

        xml_name = u'http://presto/ bsddb-get'
        xml_dom = None

        presto_interfaces = set ((u'name', u'key', ))
        
        BSDDB_DB_FLAGS = db.DB_THREAD
        BSDDB_DB_TYPE = db.DB_HASH

        def bsddb_get_presto (self, reactor):
                # open a new DB environement if there is none
                #
                reactor ('<bsddb xmlns="http://presto/">')
                if self.bsddb_DB == None and not self.bsddb_open (reactor):
                        reactor ('</bsddb>')
                        reactor ('')
                        return

                # try to get the requested key and send it 
                try:
                        reactor (self.bsddb_DB.get (
                                reactor.presto_vector[u'key'].encode (
                                        'UTF-8', 'xmlcharrefreplace'
                                        )
                                ))
                except AssertionError, excp:
                        reactor ('<excp>Assertion Error</excp>' % excp)
                except Exception, excp:
                        # send an exception, "decache" the container (and
                        # consequently close the DB environnement).
                        reactor ('<excp><![CDATA[%r]]></excp>' % excp)
                        self.xml_dom = None
                        
                # close the DB environement if this instance is
                # not cached, binded to its container by the xml_dom
                # circular reference
                #
                if self.xml_dom == None:
                        self.bsddb_DB.close ()
                        self.bsddb_DB = None
                reactor ('</bsddb>')
                reactor ('')

        presto_methods = {
                u'get': presto_synchronize ('bsddb_get_presto')
                }


class BSDDB_set (BSDDB_table, PRESTo_sync):

        xml_name = u'http://presto/ bsddb-set'
        xml_dom = None

        presto_interfaces = set ((u'name', u'key', u'value'))
        
        BSDDB_DB_FLAGS = db.DB_THREAD
        BSDDB_DB_TYPE = db.DB_HASH
        
        def bsddb_set (self, reactor):
                reactor ('<bsddb xmlns="http://presto/">')
                if self.bsddb_DB == None and not self.bsddb_open (reactor):
                        reactor ('</bsddb>')
                        return
                        
                key = reactor.presto_vector[u'key'].encode (
                        'UTF-8', 'xmlcharrefreplace'
                        )
                try:
                        self.bsddb_DB[key] = \
                                reactor.presto_vector[u'value'].encode (
                                        'UTF-8', 'xmlcharrefreplace'
                                        )
                except db.DBError, excp:
                        reactor ('<excp><![CDATA[%s]]></excp>' % excp)
                self.bsddb_DB.close ()
                self.bsddb_DB = None
                reactor ('</bsddb>')
                reactor ('')

        presto_methods = {u'set': presto_synchronize ('bsddb_set')}


class BSDDB_record (BSDDB_table, PRESTo_sync):

        xml_name = u'http://presto/ bsddb-record'
        xml_dom = None

        presto_interfaces = set ((u'name', u'recno', u'value'))
        
        BSDDB_DB_FLAGS = db.DB_THREAD
        BSDDB_DB_TYPE = db.DB_RECNO

        def bsddb_set (self, reactor):
                reactor ('<bsddb xmlns="http://presto/">')
                if self.bsddb_DB == None and not self.bsddb_open (reactor):
                        reactor ('</bsddb>')
                        return
                        
                recno = int (reactor.presto_vector[u'recno'])
                value = reactor.presto_vector[u'value'].encode (
                        'UTF-8', 'xmlcharrefreplace'
                        )
                try:
                        if value == '':
                                reactor (self.bsddb_DB.get (recno))
                        else:
                                self.bsddb_DB[recno] = value
                except db.DBError, excp:
                        reactor ('<excp><![CDATA[%s]]></excp>' % excp)
                self.bsddb_DB.close ()
                self.bsddb_DB = None
                reactor ('</bsddb>')
                reactor ('')

        presto_methods = {u'record': presto_synchronize ('bsddb_record')}


class BSDDB_cursor (BSDDB_table, PRESTo_sync):
        
        xml_name = u'http://presto/ bsddb-cursor'
        xml_dom = None

        presto_interfaces = set ((u'name', u'direction', u'count',))
        
        BSDDB_DB_FLAGS = db.DB_RDONLY | db.DB_THREAD
        BSDDB_DB_TYPE = db.DB_RECNO

        def bsddb_cursor (self, reactor):
                reactor ('<bsddb xmlns="http://presto/">')
                if self.bsddb_DB == None and not self.bsddb_open (reactor):
                        reactor ('</bsddb>')
                        reactor ('')
                        return
                        
                try:
                        count = int (reactor.presto_vector[u'count'])
                        bsddb_cursor = self.bsddb_DB.cursor ()
                        if reactor.presto_vector[u'direction'] == u'next':
                                direction = bsddb_cursor.next
                        elif reactor.presto_vector[u'direction'] == u'prev':
                                direction = bsddb_cursor.prev
                        while count:
                                item = direction ()
                                count -= 1
                                if item == None:
                                        break
                                   
                                reactor (item[1]) # dump string (usually XML)!
                except db.DBError, excp:
                        reactor ('<excp><![CDATA[%s]]></excp>' % excp)
                if self.xml_dom == None:
                        self.bsddb_DB.close ()
                        self.bsddb_DB = None
                reactor ('</bsddb>')
                reactor ('')

        presto_methods = {u'cursor': presto_synchronize ('bsddb_cursor')}


# These simple BSDDB components are supposed to address the need of
# a "flat" web database application. Many don't actually require an
# SQL server, just a convenient persistence interface for indexed 
# collections and transaction logs.
#
# This is *not* yet another object database!
#
# Just 6 methods: OPEN, SET, GET, RECORD and CURSOR.
#
# That's enough to apply BSDDB hash, recno, btree and queue tables,
# an build a simple web database just with a filesystem skeleton of 
# XML documents:
#
# bsddb/
#        open.xml -> load the interface page
#        set.xml -> set hash value string
#        get.xml -> get hash value string
#        queue.xml -> push to a queue
#        record.xml -> append a new record, get the recno string
#        cursor.xml -> browse any RECNO table using BTREE indexes
#

# TODO: a fifth favorite for real database applications - 'index' - but that
#       one is not as easy and *will* require me to better my knowledge of
#       pybsddb and its interfaces for primary and secondary indices.
#
#       concentrate on what kind of 8bit byte strings are going to fit
#       into those tables, how to code a component for HASH/BTREE/RECNO
#       database index/select.
#
#       the obvious data model seems for the general purpose case:
#
#               [(RECNO, '<relation attr="value" .../>')]
#
#       for a RECNO, finaly for each 'relation' and 'attr':
#
#               {'value': RECNO}
#
#       a BTREE index. Then be able to interpret the simple
#
#               select?attr=value&...
#
#       and pretty much nothing else. What does a shop need? A good display.
#       On the web it means "what I'm looking for should be on display".
#
#       The obvious XML application of BSDDB is to use it as an indexed
#       store, the good old XML/Object database paradigm for business
#       applications, not web search. Anyway it is only a second-line
#       database, caching as XML the SQL results fetched from a central
#       service (that's a good application of a web application peer, as
#       a transaction cache for database).
#        
#       This is a simple XML application of BSDDB, much I suspect in the
#       line (but far below) of what BSD XMLDB does. This implementation
#       may give way to something a lot better in the future, but its
#       component interfaces are stable. There is little, if no, real access
#       to the BSDDB interfaces besides common operations. It's just BSDDB
#       tables with XML UTF-8 strings inside ;-)
#

# Notes about this implementation
#
# These five classes implements each one a single basic process: create or
# get the status of a table, get or set one (key, value) pair, log a maximum
# of N pairs starting from a recno/key.
#
#        /open?name=&type=
#        /get?name=&key=
#        /set?name=&key=&value=
#        /record?name=&key=&value=
#        /cursor?name=&key=&count=&step=&index=
#
# You can construct pretty complex database web application with those five
# components. They are basically all the API required to create, browse
# and update a bsddb database made of hash tables and indexed flat files.
#
# Just link their REST interface, presto!
#
#
# RAD for web databases
#
# The purpose of bsddb_presto is to do rapid implementation of persistence
# for a variety of single-purpose functions, give them a persistent XML state
# cache an instance of that state as long as its user's session is opened,
# and use it to render the state of the function to the user (using
# a combination of CSS stylesheets, XSL or Javascript transformation).
#
# If you can write your next demo database web application with these four
# bsddb_presto functions - open, get, set, log - then it pass the test of
# a productive RAD tool for web application peers. Because 90% of the work
# is done. The PRESTo tool chain forces a development process that is centered
# on the design and implementation in parallel of presentation, programming
# and modeling.
# 
# 
# Productive for application users, database programmers and web designers. 
#
# Design and implementation happen independantly in any of the three aspects
# the process, they only share one single HTTP/XML interface. A modeler
# can add a "database document" to the PRESTo filesystem linking by XML FQN
# to the Python classes and to XSL/CSS stylesheets and Javascript by the mean
# of XML processing instruction. The modeler is the user, he does not have to
# program Python, XSLT, CSS or Javascript. XML cut and paste should be all
# the modeler has to do to change the aspect and persistent state of the
# application or application user interface he is modeling.
#
# The web designer can add functionnality to the user interface but also to
# the bsddb_presto application itself, by articulating its four interfaces.
# A designer versed only in markup language and Javascript can do a lot to
# add features, without interfering with the application's core, without
# threatening its stability or its security.
#
# Programming Python modules for Allegra's PRESTo peer is only required once
# the application has at least one working model and view. Measure twice, cut
# once, and when it has at least two models and two views, start the design
# of your Python PRESTo interfaces with inactive XML documents. While the
# application modeler and the web designer develop their parts, the programmer
# can make a few test case using a common set of XML templates.
#
# The whole process is well supported by a combination of the following
# software environment:
#       
#        Eclipse 3.0, a productive workbench for Python and XML
#
#        Python 2.4, runtime from cell-phone to OS/390 systems
#
#        Firefox 1.0.4 and other Mozilla branches
#
# With bsddb_presto, Allegra PRESTo provides a simple public infrastructure
# on which to develop distributed statefull and persistent peer network 
# applications. Like Allegra Semantic Web Peer, but also distributed
# entreprise workflows or distributed database servers.
#
#
# Optimization
# 
# All this "behind-the-scene" bsddb machinery may seem a bit of cruft added,
# but the alternative from within an HTTP peer is to carefully manage bsddb
# opened connections. Something you would do only if your application requires
# it and only once that it has reached a stable API design and data model.
#
# Do not try to cache bsddb tables or cursors at first!
#
# Let bsddb handle the cache. Tuning its interfaces will yield optimization,
# but the PRESTo interface won't move. Concentrate on writing fast algorithms
# for calls to C modules that do release the GIL and therefore do yield
# performance gains (releasing the constraints on both the CPU usage of the
# application and, via the GIL, to the asynchronous I/O processing). And do
# it only once your application APIs are stable.
#
# If you look at SWAP you will see an example of managed bsddb sessions via
# which the PNS dispatches its logs to the appropriate context's table,
# maintaining one database file open to write XML logs of the PNS statements.
# But then SWAP is not the average web database application and you might
# have more mundane urgent task at hand. Like me. For instance, I did not
# write specific classes in SWAP to handle the subscribe, post and log access
# to each context's statements database(s).
#
#
# Roadmap to usefull XML/SQL mapping
#
# There is little to add in terms of interfaces to those five fabs. A nice
# performance improvement would be to use a bsddb instead of a filesystem
# to store Allegra PRESTo's XML doclets, a la ZODB, extending the PRESTo
# folder interface to synchronous database connections.
#
# Relational database applications are better built on ... relational
# database management systems, and usually it is whatever the legacy of
# your customer is. It may be a Microsoft SQL server, a set of DB2 files
# on an OS/400, FireBird on Linux, and many other.
#
# The two pitfalls of database applications developments is bad database
# design and wrong user interface. UI is tricky and is seldom related to
# the database logic. Coupling both is the best recipe for bad database
# design, and leads directly to the populous cemetary of aborted projets.
# What makes database design fail in 99% of the case is the neglect for
# actual data samples and too much focus on the application requirements.
#
# The virtuous way to develop a relational database application is to let
# relations emerge from sample data, then develop whatever application
# of those *existing* relations is demanded by the system owner.
#
# The practical way to develop such application is to use whatever legacy
# database is available and then follow the virtuous way.
#
# So, what an Allegra Database developper should be able to do is both
# access legacy SQL servers and create new relational databases from
# their new XML document workflows, unifying both with a single web user
# interface. The benefit of Allegra in an enterprise comes with its ability
# to distribute most of the application workload on network peers. Browsing
# through an XML view of the database does require large and complex web
# application servers and local persistence makes off-line transactions
# a simple and easy thing to program, off-line browsing and search a natural
# thing to do.

# About ZODB
#
# Using BSDDB to hold a filesystem of CPython pickles is good for CFM
# system like Zope, but not of other web applications. To save calls to
# the OS's filesystem, PRESTo developpers must rather aggressively cache 
# instances than try to optimize instanciation.
#
# Then they (I!) can have the best of both worlds: 
#
# 1. reliability, flexibility and ubiquity of the filesystem as a single
#    interface to create, update, rename or delete "objects", to enforce
#    ownership between the programmer, the designer and the users of a
#    developpement or production run.
#
# 2. live instance, in a memory cache, serving fast responses without
#    having to open a file, parse it and instanciate a tree of
#    Python instances (however fast that may be).
# 
