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

from allegra import (
        loginfo, finalization, synchronizer, 
        xml_dom, xml_utf8, xml_unicode, 
        presto, presto_http
        )


class PRESTo_dom (
        xml_dom.XML_dom, loginfo.Loginfo, finalization.Finalization
        ):
        
        "BSDDB implementation of PRESTo's COM interfaces"
        
        presto_defered = None
        
        def __init__ (self, name, types={}, type=presto.PRESTo_async):
                self.xml_prefixes = {u'http://presto/': u'presto'}
                self.xml_pi = {}
                self.xml_type = type
                self.xml_types = types
                self.presto_name = name
                        
        def __repr__ (self):
                return 'presto-bsddb-dom name="%s"' % self.presto_name
        
        def sync_get (self):
                try:
                        data = self.bsddb_DB.get (self.presto_name)
                except db.DBError, excp:
                        data = '<presto:bsddb-excp/>'
                self.select_trigger ((self.async_get, (data, )))
        
        def sync_set (self, data):
                try:
                        self.bsddb_DB[self.presto_name] = data
                except db.DBError, excp:
                        pass
                self.select_trigger ((self.async_defered, ()))
                        
        def async_get (self, data):
                self.xml_parser_reset ()
                try:
                        self.xml_expat.Parse (data, 1)
                except expat.ExpatError, error:
                        self.xml_error = error
                        self.xml_parse_error ()
                        self.xml_expat = self.xml_parsed = None
                if self.xml_root == None:
                        self.xml_root = self.xml_type ()
                if self.xml_root.xml_attributes == None:
                        self.xml_root.xml_attributes = {}
                self.async_defered ()

        def async_defered (self):
                defered = self.presto_defered
                self.presto_defered = None
                for call, args in defered:
                        call (*args)

        # The PRESTo commit and rollback interfaces
        
        def presto_rollback (self, defered):
                if self.presto_defered:
                        try:
                                self.presto_defered.append (defered)
                        except:
                                return False
                        
                else:
                        self.presto_defered = [defered]
                        self.xml_root = None
                        self.synchronized ((
                                self.sync_get, (self.presto_name)
                                ))
                return True
        
        def presto_commit (self, defered):
                if self.presto_defered:
                        return False
                
                self.presto_defered = (defered, )
                self.synchronized ((self.sync_set, (
                        xml_unicode.xml_string (self.xml_root, self), 
                        )))
                return True



class BSDDB_table (presto.PRESTo_sync):
        
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
        
        # Simply creates a new bsddb table or open an existing one
        # and reports its status or an error condition. This component
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
                        
                reactor ('<stat>%s</stat>' % presto.presto_xml (
                                self.bsddb_DB.stat (), set ()
                                ))
                if self.xml_dom == None:
                        self.bsddb_DB.close ()
                        self.bsddb_DB = None
                reactor ('</bsddb>')
                reactor ('')
                
        presto_methods = {
                u'open': presto.presto_synchronize (presto_bsddb_open)
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
                        reactor ('<excp>Assertion Error</excp>')
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
                u'get': presto.presto_synchronize (presto_bsddb_get)
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

        presto_methods = {
                u'set': presto.presto_synchronize (presto_bsddb_set)
                }


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
                u'record': presto.presto_synchronize (presto_bsddb_record)
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
                u'cursor': presto.presto_synchronize ('presto_bsddb_cursor')
                }

# Note about this implementation
#
# dbopen db= type=
# dbget db= key=
# dbset db= key= value=
# dblog db= value=
# dbrecord db= index= value=
# dbindex db= key= index=
# dbcursor record= index= move= count=