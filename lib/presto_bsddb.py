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


class BSDDB_table (PRESTo_sync):
        
        BSDDB_DB_TYPES = {
                u'BTREE': db.DB_BTREE,
                u'HASH': db.DB_HASH,
                u'RECNO': db.DB_RECNO,
                }
        BSDDB_DB_TYPE = db.DB_HASH
        BSDDB_OPEN_FLAGS = db.DB_THREAD # TODO: check if that can be relaxed

        bsddb_DB = None

        xml_name = u'http://presto/ bsddb-table'
        xml_dom = None
        
        presto_interfaces = set ((u'PRESTo', u'name', u'type'))
        
        def xml_valid (self, dom):
                if self.xml_parent != None:
                        self.xml_dom = dom
                        self.xml_parent ().presto_methods[
                                self.xml_name.split (u' ')[1]
                                ] = self

        def presto_bsddb_table (self, reactor):
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


class BSDDB_open (BSDDB_table):
        
        # Simply creates a new bsddb table or an old oneif it exists
        # and reports its status or an error condition. This object
        # may be completely transient and used as a single interface
        # to create many database tables of different types, or to check
        # their status.
        
        xml_name = u'http://presto/ bsddb-open'

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

        def presto_bsddb_open (self, reactor):
                reactor ('<bsddb xmlns="http://presto/">')
                if (
                        self.bsddb_DB == None and 
                        not self.presto_bsddb_table (reactor)
                        ):
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
                
        def __call__ (self, root, reactor):
                return self.presto_synchronized (
                        reactor, 'presto_bsddb_open'
                        )
                
        presto_methods = {
                u'open': presto_synchronize ('presto_bsddb_open')
                }


class BSDDB_get (BSDDB_table):

        xml_name = u'http://presto/ bsddb-get'
        xml_dom = None

        presto_interfaces = set ((u'name', u'key', ))
        
        BSDDB_DB_FLAGS = db.DB_THREAD
        BSDDB_DB_TYPE = db.DB_HASH

        def presto_bsddb_get (self, reactor):
                # open a new DB environement if there is none
                #
                reactor ('<bsddb xmlns="http://presto/">')
                if (
                        self.bsddb_DB == None and 
                        not self.presto_bsddb_table (reactor)
                        ):
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

        def __call__ (self, root, reactor):
                return self.presto_synchronized (reactor, 'presto_bsddb_get')
                
        presto_methods = {
                u'get': presto_synchronize ('presto_bsddb_get')
                }


class BSDDB_set (BSDDB_table):

        xml_name = u'http://presto/ bsddb-set'
        xml_dom = None

        presto_interfaces = set ((u'name', u'key', u'value'))
        
        BSDDB_DB_FLAGS = db.DB_THREAD
        BSDDB_DB_TYPE = db.DB_HASH
        
        def presto_bsddb_set (self, reactor):
                reactor ('<bsddb xmlns="http://presto/">')
                if (
                        self.bsddb_DB == None and 
                        not self.presto_bsddb_table (reactor)
                        ):
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

        def __call__ (self, root, reactor):
                return self.presto_synchronized (reactor, 'presto_bsddb_set')
                
        presto_methods = {u'set': presto_synchronize ('presto_bsddb_set')}


class BSDDB_record (BSDDB_table):

        xml_name = u'http://presto/ bsddb-record'
        xml_dom = None

        presto_interfaces = set ((u'name', u'recno', u'value'))
        
        BSDDB_DB_FLAGS = db.DB_THREAD
        BSDDB_DB_TYPE = db.DB_RECNO

        def presto_bsddb_record (self, reactor):
                reactor ('<bsddb xmlns="http://presto/">')
                if (
                        self.bsddb_DB == None and 
                        not self.presto_bsddb_table (reactor)
                        ):
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

        presto_methods = {
                u'record': presto_synchronize ('presto_bsddb_record')
                }


class BSDDB_cursor (BSDDB_table):
        
        xml_name = u'http://presto/ bsddb-cursor'
        xml_dom = None

        presto_interfaces = set ((u'name', u'direction', u'count',))
        
        BSDDB_DB_FLAGS = db.DB_RDONLY | db.DB_THREAD
        BSDDB_DB_TYPE = db.DB_RECNO

        def presto_bsddb_cursor (self, reactor):
                reactor ('<bsddb xmlns="http://presto/">')
                if (
                        self.bsddb_DB == None and 
                        not self.presto_bsddb_table (reactor)
                        ):
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

        presto_methods = {
                u'cursor': presto_synchronize ('presto_bsddb_cursor')
                }
