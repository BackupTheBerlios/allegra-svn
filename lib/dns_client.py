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

"http://laurentszyster.be/blog/dns_client/"

import time, re

from allegra import async_loop, async_core, timeouts, ip_peer


# a bit of OS specific code to get the addresses of the DNS name
# servers for the host system

def _peers ():
        # called once
        import os
        if os.name == 'nt':
                # avoid _winreg: parse XP's "ipconfig /all" instead ...
                # 
                m = re.search (
                        'DNS[.\s]+?:\s+?'
                        '([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+).+?'
                        '([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)?',
                        os.popen ('ipconfig /all','r').read (),
                        flags=re.DOTALL
                        )
                if m:
                        return m.groups ()
                    
        elif os.name == 'posix':
                return re.compile ('nameserver[ ]+(.+)').findall (
                        open ('/etc/resolv.conf', 'r').read ()
                        )
                        
        return ['127.0.0.1'] # expect a local dns cache!

# unpack and parse names, ttl and preference from resource DNS records

def _skip_name (datagram, pos):
        while 1:
                ll = ord (datagram[pos])
                if (ll&0xc0):
                        # compression
                        return pos + 2
                
                elif ll == 0:
                        pos += 1
                        break
                else:
                        pos += ll + 1
        return pos

def _unpack_name (datagram ,pos):
        n = []
        while 1:
                ll = ord (datagram[pos])
                if (ll&0xc0):
                        # compression
                        pos = (ll&0x3f << 8) + (ord (datagram[pos+1]))
                elif ll == 0:
                        break
                
                else:
                        pos += 1
                        n.append (datagram[pos:pos+ll])
                        pos += ll
        return '.'.join (n)

def _unpack_ttl (datagram, pos):
        return reduce (
                lambda x,y: (x<<8)|y, map (ord, datagram[pos:pos+4])
                )

def _unpack_preference (datagram, pos):
        return reduce (
                lambda x,y: (x<<8)|y, map (ord, datagram[pos:pos+2])
                )


# The "inner" API, to be extended ...

class Reactor (object):

        dns_failover = 0

        dns_when = dns_uid = dns_peer = dns_resolve = \
                dns_ttl = dns_response = dns_resources = None

        def __init__ (self, question, servers):
                self.dns_question = question
                self.dns_servers = servers
                self.dns_peer = (servers[0], 53)

        def dns_unpack (self, datagram):
                self.dns_response = datagram
                # count resources announced
                ancount = (ord (datagram[6])<<8) + (ord (datagram[7]))
                if ancount:
                        # skip question, first name starts at 12, this is
                        # followed by QTYPE and QCLASS
                        pos = _skip_name (datagram, 12) + 4
                        self.dns_resources = []
                        for an in range (ancount):
                                pos = _skip_name (datagram, pos)
                                if self.dns_collect (datagram, pos):
                                        # unpack all records until the 
                                        # reactor signal it's done with
                                        # the response
                                        break
                                        
                                # skip over TYPE, CLASS, TTL, RDLENGTH, RDATA
                                pos += 8
                                pos += 2 + (ord (datagram[pos])<<8) + (
                                        ord (datagram[pos+1])
                                        )
                        return self.dns_collected ()

                return False # error

        def dns_collect (self, datagram, pos):
                return False

        def dns_collected (self):
                return True


class _A (Reactor):

        DNS_DATAGRAM = (
                '%c%c\001\000\000\001\000\000\000\000\000\000%s\000'
                '\000\001\000\001'
                )

        def dns_collect (self, datagram, pos):                        
                if datagram[pos:pos+4] == '\000\001\000\001':
                        self.dns_ttl = _unpack_ttl (datagram, pos+4)
                        self.dns_resources.append (
                                '%d.%d.%d.%d' % tuple (
                                        map (ord, datagram[pos+10:pos+14])
                                        )
                                )
                        return True

                return False
        

class _NS (Reactor):

        DNS_DATAGRAM = (
                '%c%c\001\000\000\001\000\000\000\000\000\000%s\000'
                '\000\002\000\001'
                )

        def dns_collect (self, datagram, pos):
                if datagram[pos:pos+4]== '\000\002\000\001':
                        self.dns_resources.append ((
                                _unpack_ttl (datagram, pos+4),
                                _unpack_name (datagram, pos+10)
                                ))
                return False

        def dns_collected (self):
                if self.dns_resources:
                        self.dns_resources.sort ()
                        self.dns_ttl = self.dns_resources[0][0]
                        self.dns_resources = tuple ([
                                rr[1] for rr in self.dns_resources 
                                ])
                        return True

                return False


class _MX (Reactor):

        DNS_DATAGRAM = (
                '%c%c\001\000\000\001\000\000\000\000\000\000%s\000'
                '\000\017\000\001'
                )

        def dns_collect (self, datagram, pos):
                if datagram[pos:pos+4]== '\000\017\000\001':
                        self.dns_resources.append ((
                                _unpack_preference (datagram, pos+10),
                                _unpack_name (datagram, pos+12),
                                _unpack_ttl (datagram, pos+4)
                                ))
                return False
                
        def dns_collected (self):
                if not self.dns_resources:
                        return False
                        
                if len (self.dns_resources) > 1:
                        self.dns_resources.sort ()
                        if self.dns_resources[0][0] < self.dns_resources[-1][0]:
                                self.dns_resources.reverse ()
                self.dns_ttl = self.dns_resources[0][2]
                self.dns_resources = tuple ([
                        rr[1] for rr in self.dns_resources 
                        ])
                return True


class _PTR (Reactor):

        DNS_DATAGRAM = (
                '%c%c\001\000\000\001\000\000\000\000\000\000%s\000'
                '\000\014\000\001'
                )

        def dns_collect (self, datagram, pos):
                if datagram[pos:pos+4]== '\000\014\000\001':
                        self.dns_ttl = _unpack_ttl (datagram, pos+4)
                        self.dns_resources.append (
                                _unpack_name (datagram, pos+10)
                                )
                        return True

                return False


class Resolver (async_core.Dispatcher, timeouts.Timeouts):

        DNS_reactors = {'A': _A, 'NS': _NS, 'MX': _MX, 'PTR': _PTR}

        def __init__ (
                self, servers, failover=1, timeout=2, precision=1, ip=None
                ):
                self.dns_servers = servers
                self.dns_failover = failover
                timeouts.Timeouts.__init__ (self, timeout, precision)
                self.dns_ip = ip
                self.dns_sent = 0
                self.dns_cache = {}
                self.dns_pending = {}
                
        def __repr__ (self):
                return 'dns-client id="%x"' % id (self)
                        
        def __call__ (self, question, resolve):
                # first check the cache for a valid response or a 
                # pending request ...
                #
                try:
                        request = self.dns_cache.get[question]
                except:
                        when = time.time ()
                else:
                        if request.dns_resolve != None:
                                # ... either resolve with pending ...
                                request.dns_resolve.append (resolve)
                                return
                                
                        when = time.time ()
                        if request.dns_ttl < when:
                                # ... or resolve now.
                                resolve (request)
                                return

                # no cache entry, send a new request
                #
                request = self.DNS_reactors[question[1]] (
                        question, self.dns_servers
                        )
                # request.dns_client = self
                request.dns_resolve = [resolve]
                self.dns_send (request, when)
                
        #def close (self):
        #        async_core.Dispatcher.close (self)
                
        def writable (self):
                return False # UDP/IP is never writable
                                
        def handle_read (self):
                # match the datagram's UID with the pending DNS requests
                #
                datagram, peer = self.recvfrom (512)
                if peer == None:
                        return
                
                uid = (ord (datagram[0]) << 8) + ord (datagram[1])
                try:
                        request = self.dns_pending.pop (uid)
                except:
                        self.log (
                                'redundant ip="%s" port="%d"' % peer, 
                                'security'
                                )
                        return
                
                if request.dns_peer != peer:
                        self.log (
                                'impersonate ip="%s" port="%d"' % peer, 
                                'security'
                                )
                        return
                        
                # consider the DNS request as answered: unpack and cache 
                # the response, ...
                #
                assert None == self.log (
                        'signal ip="%s" port="%d"' % peer, 'debug'
                        )
                request.dns_unpack (datagram)
                self.dns_finalize (request)

        def dns_send (self, request, when):
                if self.socket == None:
                        if not ip_peer.udp_bind (self, self.dns_ip):
                                self.dns_finalize (request)
                                #
                                # in case of failure, just keep trying.

                request.dns_when = when
                request.dns_uid = uid = self.dns_sent % (1<<16)
                self.dns_pending[uid] = request
                self.sendto (
                        request.DNS_DATAGRAM % (
                                chr ((uid>>8)&0xff), chr (uid&0xff),
                                ''.join ([
                                        '%c%s' % (chr (len (part)), part)
                                        for part 
                                        in request.dns_question[0].split ('.')
                                        ])
                                ), request.dns_peer
                        )
                self.dns_sent += 1
                self.timeouts_start (when)
                self.timeouts_deque.append ((when, uid))
                assert None == self.log (
                        'send ip="%s" port="%d" pending="%d" sent="%d"' % (
                                request.dns_peer[0], request.dns_peer[1],
                                len (self.dns_pending), self.dns_sent
                                ), 'debug'
                        )
                        
        def timeouts_timeout (self, uid):
                try:
                        request = self.dns_pending.pop (uid)
                except KeyError:
                        return
                        
                request.dns_failover += 1
                if request.dns_failover < (
                        len (request.dns_servers) * self.dns_failover
                        ):
                        # continue with the next peer and a new time
                        request.dns_peer = (
                                request.dns_servers[
                                        request.dns_failover % len (
                                                request.dns_servers
                                                )
                                        ], 53
                                )
                        self.dns_send (request, time.time ())
                else:
                        # ... or finalize ...
                        self.dns_finalize (request)

        def dns_finalize (self, request):
                for resolve in request.dns_resolve:
                        resolve (request)
                request.dns_resolve = None

        def timeouts_stop (self):
                # self.timeouts_timeout = None
                self.handle_close ()

# The convenience "outer API", to be applied ...

def resolver ():
        addresses = _peers ()
        if addresses:
                return Resolver (addresses)

        raise Exception ('No Resolver Address Available')


lookup = resolver () # never finalized, but not allways binded


def RESOLVED (request):
        assert None == lookup.log ('%r' % request.__dict__, 'debug')

def first_mail_lookup (name, resolved=RESOLVED):
        def resolved_MX (request_MX):
                try:
                        mx1 = request_MX.dns_resources[0]
                except:
                        resolved (None)
                        return
                
                lookup ((mx1, 'A'), resolved)
        lookup ((name, 'MX'), resolved_MX)            


def REVERSED (ip): 
        assert None == lookup.log ('%r' % ip, 'debug')

def reverse_lookup (name, reversed):
        def resolved_A (request_A):
                try:
                        ip = request_A.dns_resources[0]
                except:
                        reversed (None)
                        return
                
                def resolved_PTR (request_PTR):
                        try:
                                cn = request_PTR.dns_resources[0]
                        except:
                                reversed (None)
                                return
                        
                        def resolved_A_PTR (request_A_PTR):
                                try:
                                        iprev = request_A_PTR.dns_resources[0]
                                except:
                                        reversed (None)
                                        return
                                
                                if iprev == ip:
                                        reversed (ip)
                                else:
                                        reversed (None)
                                        
                        lookup ((
                                request_PTR.dns_resources[0], 'A'
                                ), resolved_A_PTR)
                                
                lookup ((
                        ip_peer.in_addr_arpa (ip), 'PTR'
                        ), resolved_PTR)
                        
        lookup ((name, 'A'), resolved_A)
                
                
if __name__ == '__main__':
        import sys
        from allegra import netstring, loginfo, finalization
        assert None == loginfo.log (
                'Allegra DNS/UDP Client'
                ' - Copyright 2005 Laurent A.V. Szyster | Copyleft GPL 2.0',
                'info'
                )
        if len (sys.argv) < 2:
                assert None == loginfo.log (
                        'dns_client.py NAME [TYPE=A [SERVER [SERVER ...]]',
                        'info'
                        )
                sys.exit (1)
                
        def resource_resolved (request):
                model = list (request.dns_question)
                if request.dns_resources == None:
                        model.append ('')
                elif len (request.dns_resources) > 1:
                        model.append (netstring.encode (
                                request.dns_resources
                                ))
                elif request.dns_resources:
                        model.append (request.dns_resources[0])
                else:
                        model.append ('')
                model.append (request.dns_peer[0])
                loginfo.log (netstring.encode (model))
                
        def reverse_resolved (ip):
                if ip != None:
                        loginfo.log (ip)
                
        if len (sys.argv) > 3:
                servers = sys.argv[3:]
        else:
                servers = _peers ()
        if len (sys.argv) > 2:
                question = tuple (sys.argv[1:3])
        else:
                question = (sys.argv[1], 'A')
        if question[1] == 'reverse':
                reverse_lookup (
                        question[0], reverse_resolved, Resolver (servers)
                        )
        else:
                Resolver (servers) (question, resource_resolved)
        async_loop.dispatch ()
        assert None == finalization.collect ()
        sys.exit (0)