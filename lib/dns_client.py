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

import os, time, re

from allegra import async_loop, async_core, timeouts, ip_peer


def _peers ():
        "get the addresses of the DNS name servers for the host system"
        if os.name == 'nt':
                # avoid _winreg: parse XP's "ipconfig /all" instead ...
                # 
                m = re.search (
                        'DNS[.\s\w]+?:\s+?'
                        '([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+).+?'
                        '([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)?',
                        os.popen ('ipconfig /all','r').read (),
                        flags=re.DOTALL
                        )
                if m:
                        return [s for s in m.groups () if s != None]
                    
        elif os.name == 'posix':
                return re.compile ('nameserver[ ]+(.+)').findall (
                        open ('/etc/resolv.conf', 'r').read ()
                        )
                        
        return ['127.0.0.1'] # expect a local dns cache!


def _skip_name (datagram, pos):
        "skip a name in the resource record at pos"
        while 1:
                ll = ord (datagram[pos])
                if (ll&0xc0):
                        return pos + 2 # compression
                
                elif ll == 0:
                        pos += 1
                        break
                
                else:
                        pos += ll + 1
        return pos

def _unpack_name (datagram ,pos):
        "unpack a name from the resource record"
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
        "unpack a TTL from the resource record"
        return reduce (
                lambda x,y: (x<<8)|y, map (ord, datagram[pos:pos+4])
                )

def _unpack_preference (datagram, pos):
        "unpack a preference order from the resource record"
        return reduce (
                lambda x,y: (x<<8)|y, map (ord, datagram[pos:pos+2])
                )


# The "inner" API, to be extended ...

class Request (object):

        dns_failover = 0

        dns_when = dns_uid = dns_peer = dns_resolve = \
                dns_ttl = dns_response = dns_resources = None

        def __init__ (self, question, servers):
                self.dns_question = question
                self.dns_servers = servers
                self.dns_peer = (servers[0], 53)

        def dns_unpack (self, datagram):
                "unpack the resource records from a response datagram"
                self.dns_response = datagram
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


class Request_A (Request):

        DNS_DATAGRAM = (
                '%c%c\001\000\000\001\000\000\000\000\000\000%s\000'
                '\000\001\000\001'
                )

        def dns_collect (self, datagram, pos):
                "unpack an A resource record at pos"
                if datagram[pos:pos+4] == '\000\001\000\001':
                        self.dns_ttl = _unpack_ttl (datagram, pos+4)
                        self.dns_resources.append (
                                '%d.%d.%d.%d' % tuple (
                                        map (ord, datagram[pos+10:pos+14])
                                        )
                                )
                        return True

                return False
        

class Request_NS (Request):

        DNS_DATAGRAM = (
                '%c%c\001\000\000\001\000\000\000\000\000\000%s\000'
                '\000\002\000\001'
                )

        def dns_collect (self, datagram, pos):
                "unpack an NS resource record at pos"
                if datagram[pos:pos+4]== '\000\002\000\001':
                        self.dns_resources.append ((
                                _unpack_ttl (datagram, pos+4),
                                _unpack_name (datagram, pos+10)
                                ))
                return False

        def dns_collected (self):
                "sort the NS resource records by preference, set TTL"
                if self.dns_resources:
                        self.dns_resources.sort ()
                        self.dns_ttl = self.dns_resources[0][0]
                        self.dns_resources = [
                                rr[1] for rr in self.dns_resources 
                                ]
                        return True

                return False


class Request_MX (Request):

        DNS_DATAGRAM = (
                '%c%c\001\000\000\001\000\000\000\000\000\000%s\000'
                '\000\017\000\001'
                )

        def dns_collect (self, datagram, pos):
                "unpack an MX resource record at pos"
                if datagram[pos:pos+4]== '\000\017\000\001':
                        self.dns_resources.append ((
                                _unpack_preference (datagram, pos+10),
                                _unpack_name (datagram, pos+12),
                                _unpack_ttl (datagram, pos+4)
                                ))
                return False
                
        def dns_collected (self):
                "sort the MX resource records by preference, set TTL"
                if not self.dns_resources:
                        return False
                        
                if len (self.dns_resources) > 1:
                        self.dns_resources.sort ()
                        if self.dns_resources[0][0] < self.dns_resources[-1][0]:
                                self.dns_resources.reverse ()
                self.dns_ttl = self.dns_resources[0][2]
                self.dns_resources = [
                        rr[1] for rr in self.dns_resources 
                        ]
                return True


class Request_PTR (Request):

        DNS_DATAGRAM = (
                '%c%c\001\000\000\001\000\000\000\000\000\000%s\000'
                '\000\014\000\001'
                )

        def dns_collect (self, datagram, pos):
                "unpack a PTR resource record at pos"
                if datagram[pos:pos+4]== '\000\014\000\001':
                        self.dns_ttl = _unpack_ttl (datagram, pos+4)
                        self.dns_resources.append (
                                _unpack_name (datagram, pos+10)
                                )
                        return True

                return False


class Resolver (async_core.Dispatcher, timeouts.Timeouts):

        DNS_requests = {
                'A': Request_A, 
                'NS': Request_NS, 
                'MX': Request_MX, 
                'PTR': Request_PTR
                }

        dns_ip = None
        dns_sent = 0
        dns_failover = 1

        def __init__ (self, servers):
                self.dns_servers = servers
                self.dns_cache = {}
                self.dns_pending = {}
                timeouts.Timeouts.__init__ (self, 2, 1)
                
        def __repr__ (self):
                return 'dns-client id="%x"' % id (self)
                        
        def __call__ (self, question, resolve, servers=None):
                "resolve from the cache first, maybe send a new request"
                # first check the cache for a valid response or a 
                # pending request ...
                try:
                        request = self.dns_cache[question]
                except KeyError:
                        when = time.time ()
                else:
                        if request.dns_resolve != None:
                                # ... either resolve with pending ...
                                request.dns_resolve.append (resolve)
                                return
                                
                        when = time.time ()
                        if request.dns_when + request.dns_ttl > when:
                                # ... or resolve now.
                                resolve (request)
                                return

                # no cache entry, send a new request
                request = self.DNS_requests[question[1]] (
                        question, servers or self.dns_servers
                        )
                request.dns_resolve = [resolve]
                self.dns_send (request, when)
                
        def writable (self):
                "UDP/IP is never writable"
                return False
                                
        def handle_read (self):
                "handle valid incoming responses, log irrelevant datagrams"
                datagram, peer = self.recvfrom (512)
                if peer == None:
                        return
                
                # match the datagram's UID with the pending DNS requests
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
                assert None == self.log (
                        'signal ip="%s" port="%d"' % peer, 'debug'
                        )
                request.dns_unpack (datagram)
                self.dns_finalize (request)

        def dns_send (self, request, when):
                "try to send a request, maybe connect the dispatcher"
                if self.socket == None:
                        if self.dns_connect ():
                                self.timeouts_start (when)
                        else:
                                self.dns_finalize (request)
                                return

                request.dns_when = when
                request.dns_uid = uid = self.dns_sent % 65536
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
                self.timeouts_deque.append ((when, uid))
                assert None == self.log (
                        'send ip="%s" port="%d" pending="%d" sent="%d"' % (
                                request.dns_peer[0], request.dns_peer[1],
                                len (self.dns_pending), self.dns_sent
                                ), 'debug'
                        )
                        
        def dns_connect (self):
                "bind the dispatcher to a UDP/IP socket"
                return ip_peer.udp_bind (self, self.dns_ip)
                        
        def timeouts_timeout (self, uid):
                "handle a request's timeout: drop, failover or finalize"
                try:
                        request = self.dns_pending.pop (uid)
                except KeyError:
                        return
                        
                request.dns_failover += 1
                if request.dns_failover < (
                        len (request.dns_servers) * self.dns_failover
                        ):
                        request.dns_peer = (
                                request.dns_servers[
                                        request.dns_failover % len (
                                                request.dns_servers
                                                )
                                        ], 53
                                )
                        self.dns_send (request, time.time ())
                else:
                        self.dns_finalize (request)

        def dns_finalize (self, request):
                "call back all resolution handlers for this request"
                defered = request.dns_resolve
                del request.dns_resolve
                if request.dns_response:
                        self.dns_cache[request.dns_question] = request
                        del request.dns_response
                for resolve in defered:
                        resolve (request)

        def timeouts_stop (self):
                "close the dispatcher when all requests have timed out"
                self.handle_close ()


lookup = Resolver (_peers ()) # never finalized, but not allways binded

# This is a usefull asynchronous DNS/UDP client for applications in just
# four hundreds lines of Python with licence, spacing and docstrings.
#
# DNS/TCP is not a usefull application of a Domain Name System: either
# you're on a local network where you can size your DNS server right or
# your application will simply add more weight to an overloaded server.
#
# On a public network of peers DNS/TCP makes little sense. If you really
# need this stuff, subclass the dns_send, dns_connect and handle_read
# methods to send and receive datagrams along TCP/IP stream connections.
#
# The rest of the implementation can be reused.
#
# Actually, it can also be applied to program a resolver. But not just a
# simple DNS resolver: djbdns is allready available for virtually all POSIX 
# systems (and I doubt you would want Windows to handle your DNS ;-)