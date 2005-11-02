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

# TODO: handle PTR right, handle non-existing domain/host and other
#        DNS error conditions, change the DNS predicates to QCLASS
#        and QTYPE values? ...

import time

from allegra import async_loop, udp_channel


# unpack and parse names, ttl and preference from resource DNS records

def dns_skip_name (datagram, pos):
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

def dns_unpack_name (datagram ,pos):
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

def dns_unpack_ttl (datagram, pos):
        return reduce (
                lambda x,y: (x<<8)|y, map (ord, datagram[pos:pos+4])
                )

def dns_unpack_preference (datagram, pos):
        return reduce (
                lambda x,y: (x<<8)|y, map (ord, datagram[pos:pos+2])
                )


# The DNS request

class DNS_request:

        dns_failover = 0

        dns_when = dns_uid = dns_peer = dns_resolve = \
                dns_ttl = dns_response = dns_resources = None

        def __init__ (self, question, servers):
                self.dns_question = question
                self.dns_servers = servers

        def udp_datagram (self):
                return (
                        self.DNS_DATAGRAM % (
                                chr ((self.dns_uid>>8)&0xff),
                                chr (self.dns_uid&0xff),
                                ''.join ([
                                        '%c%s' % (chr (len (part)), part)
                                        for part 
                                        in self.dns_question[0].split ('.')
                                        ])
                                )
                        )

        def dns_unpack (self, datagram):
                self.dns_response = datagram
                ancount = (ord (datagram[6])<<8) + (ord (datagram[7]))
                # skip question, first name starts at 12, this is followed
                # by QTYPE and QCLASS
                if ancount:
                        pos = dns_skip_name (datagram, 12) + 4
                        self.dns_resources = []
                        # we are looking very specifically for one TYPE and
                        # one CLASS
                        for an in range (ancount):
                                pos = dns_skip_name (datagram, pos)
                                if self.dns_unpack_continue (datagram, pos):
                                        break
                                        
                                # skip over TYPE, CLASS, TTL, RDLENGTH, RDATA
                                pos += 8
                                pos += 2 + (ord (datagram[pos])<<8) + (
                                        ord (datagram[pos+1])
                                        )
                        return self.dns_unpack_end ()

                return False # error

        def dns_unpack_continue (self, datagram, pos):
                return False

        def dns_unpack_end (self):
                return True

        def dns_continue (self, when):
                try:
                        del self.dns_client.dns_pending[self.dns_uid]
                except KeyError:
                        for resolve in self.dns_resolve:
                                resolve (self)
                        self.dns_resolve = None
                        if len (self.dns_client.dns_pending) == 0:
                                self.dns_client.close ()
                        self.dns_client = None
                        return
                        
                self.dns_failover += 1
                if self.dns_failover < (
                        len (self.dns_servers) * self.dns_client.dns_failover
                        ):
                        # continue with the next peer and a new time
                        self.dns_peer = (
                                self.dns_servers[
                                        self.dns_failover % len (
                                                self.dns_servers
                                                )
                                        ], 53
                                )
                        self.dns_client.dns_send (self, time.time ())
                else:
                        # ... or finalize ...
                        del self.dns_client # break circular ref?


class DNS_request_A (DNS_request):

        DNS_DATAGRAM = (
                '%c%c\001\000\000\001\000\000\000\000\000\000%s\000'
                '\000\001\000\001'
                )

        def dns_unpack_continue (self, datagram, pos):                        
                if datagram[pos:pos+4] == '\000\001\000\001':
                        self.dns_ttl = dns_unpack_ttl (datagram, pos+4)
                        self.dns_resources.append (
                                '%d.%d.%d.%d' % tuple (
                                        map (ord, datagram[pos+10:pos+14])
                                        )
                                )
                        return True

                return False
        

class DNS_request_NS (DNS_request):

        DNS_DATAGRAM = (
                '%c%c\001\000\000\001\000\000\000\000\000\000%s\000'
                '\000\002\000\001'
                )

        def dns_unpack_continue (self, datagram, pos):
                if datagram[pos:pos+4]== '\000\002\000\001':
                        self.dns_resources.append ((
                                dns_unpack_ttl (datagram, pos+4),
                                dns_unpack_name (datagram, pos+10)
                                ))
                return False

        def dns_unpack_end (self):
                if self.dns_resources:
                        self.dns_resources.sort ()
                        self.dns_ttl = self.dns_resources[0][0]
                        self.dns_resources = tuple ([
                                rr[1] for rr in self.dns_resources 
                                ])
                        return True

                return False


class DNS_request_MX (DNS_request):

        DNS_DATAGRAM = (
                '%c%c\001\000\000\001\000\000\000\000\000\000%s\000'
                '\000\017\000\001'
                )

        def dns_unpack_continue (self, datagram, pos):
                if datagram[pos:pos+4]== '\000\017\000\001':
                        self.dns_resources.append ((
                                dns_unpack_preference (datagram, pos+10),
                                dns_unpack_name (datagram, pos+12),
                                dns_unpack_ttl (datagram, pos+4)
                                ))
                return False
                
        def dns_unpack_end (self):
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


class DNS_request_PTR (DNS_request):

        DNS_DATAGRAM = (
                '%c%c\001\000\000\001\000\000\000\000\000\000%s\000'
                '\000\014\000\001'
                )

        def dns_unpack_continue (self, datagram, pos):
                if datagram[pos:pos+4]== '\000\014\000\001':
                        self.dns_ttl = dns_unpack_ttl (datagram, pos+4)
                        self.dns_resources.append (
                                dns_unpack_name (datagram, pos+10)
                                )
                        return True

                return False


DNS_requests = {
        'A': DNS_request_A,
        'NS': DNS_request_NS,
        'MX': DNS_request_MX,
        'PTR': DNS_request_PTR,
        }


class DNS_client (udp_channel.UDP_dispatcher):

        udp_datagram_size = 512

        # Parameters
        #
        dns_timeout = 1
        #
        # one second timeout, enough to notice the delay, reduce to a lower
        # figure as you expand the number of servers and failovers.
        #
        # check for inactive DNS client after 1 seconds and close if no
        # pending requests. re-open the channel at will, binding each time
        # to a new port with a new socket.
        #
        # Note:
        #
        # In effect, a DNS client will be kept alive 1 seconds after the 
        # first request and at most 1 seconds after the last one.
        #
        # Practically, this is the desired behaviour of a decent DNS cache, 
        # bind only when miss and keep alive if there is a high load (like
        # a web proxy or an smtp relay).
        #
        # A DNS client waits for the first request before binding, and then
        # only starts to defer for dns_keep_alive the close_when_done 
        # event. 

        def __init__ (self, servers, ip=None):
                self.dns_sent = 0
                self.dns_pending = {}
                self.dns_cache = {}
                self.dns_servers = servers
                self.dns_ip = ip
                
        def __repr__ (self):
                return '<dns-client pending="%d" sent="%d"/>' % (
                        len (self.dns_pending), self.dns_sent
                        )
                        
        def dns_resolve (self, question, resolve):
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

                # no cache entry, maybe bind and send a new request
                #
                if not self.connected:
                        self.dns_bind (self.dns_ip)
                request = DNS_requests[question[1]] (
                        question, self.dns_servers
                        )
                request.dns_client = self
                request.dns_resolve = [resolve]
                self.dns_send (request, when)
                return
                                
        def dns_bind (self, ip):
                if ip == None:
                        import socket
                        ip = socket.gethostbyname (socket.gethostname ())
                udp_channel.UDP_dispatcher.__init__ (self, ip)

        def dns_send (self, request, when):
                request.dns_when = when
                request.dns_uid = self.dns_sent % (1<<16)
                request.dns_peer = (request.dns_servers[0], 53)
                self.dns_pending[request.dns_uid] = request
                self.sendto (request.udp_datagram (), request.dns_peer)
                async_loop.async_schedule (
                        request.dns_when + self.dns_timeout,
                        request.dns_continue
                        )
                self.dns_sent += 1

        def handle_read (self):
                # match the datagram's UID with the pending DNS requests
                #
                datagram, peer = self.recvfrom ()
                uid = (ord (datagram[0]) << 8) + ord (datagram[1])
                dns_request = self.dns_pending.pop (uid)
                if dns_request == None or dns_request.dns_peer != peer:
                        assert None == self.log (
                                '<noise ip="%s" port="%d"/>' % peer, ''
                                )
                        return # log any unsolicitted requests!
                        
                # consider the DNS request as answered: unpack and cache 
                # the response, ...
                #
                assert None == self.log (
                        '<signal ip="%s" port="%d"/>' % peer, ''
                        )
                dns_request.dns_unpack (datagram)

# a bit of OS specific code to get the addresses of the DNS name
# servers for the host system

def dns_servers ():
        import os
        if os.name == 'nt':
                # parse "ipconfig /all" instead accessing the Win32 API
                import re
                m = re.search (
                        'DNS[.\s]+?:\s+?'
                        '([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+).+?'
                        '([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)',
                        os.popen ('ipconfig /all','r').read (),
                        flags=re.DOTALL
                        )
                if m:
                        return m.groups ()
                    
        else:
                # TODO: parse /etc/resolve.conf for UNIX-like systems,
                #       suppose a simple dns local cache ...
                #
                pass
        return ['127.0.0.1']


if __name__ == '__main__':
        import sys
        assert None == sys.stderr.write (
                'Allegra DNS/UDP Client'
                ' - Copyright 2005 Laurent A.V. Szyster'
                ' | Copyleft GPL 2.0\n...\n'
                )
        from allegra.netstring import netstring_encode, netstrings_encode
        def resolve (request):
                sp = netstrings_encode (request.dns_question)
                c = request.dns_peer[0]
                c = '%d:%s,' % (len (c), c)
                if request.dns_resources == None:
                        encoded = sp + '0:,' + c
                else:
                        encoded = netstrings_encode ([
                                sp + ('%d:%s,' % (len(o), o)) + c
                                for o in request.dns_resources
                                ])
                sys.stdout.write (
                        '%d:%s,' % (len (encoded), encoded)
                        )
                sys.stderr.write ('\n')
        try:
                servers = sys.argv[3:]
        except:
                servers = dns_servers ()
        dns_resolver = DNS_client (servers)
        if len (sys.argv) > 1:
                if len (sys.argv) > 2:
                        dns_resolver.dns_resolve (
                                tuple (sys.argv[1:3]), resolve
                                )
                else:
                        dns_resolver.dns_resolve (
                                (sys.argv[1], 'A'), resolve
                                )
        else:
                dns_resolver.dns_resolve (
                        ('localhost', 'A'), resolve
                        )
        async_loop.loop ()
        
        
# Note about this implementation
#
# This is a very "strict" DNS client indeed, because it will wait all the
# timeout period set before finalization of the request instance it manages.
#
# Effectively, dns_client.py wait for the full timeout for requests that do
# not belong to its cache and only then continue, callback the resolver or
# do whatever was assigned to the request instance. Cached entry on the 
# contrary are resolved immediately, as fast as it is possible.
#
# Practically this DNS client is only very slow once in a while and blazing 
# fast thereafter. It is a good client for any DNS system, and it supports
# a simple PNS/DNS peer that safeguard DNS resolution.
#
# Allegra's DNS client is designed to provide a cache and support recursive
# domain name resolution or domain MX lookup. Its design is inspired from 
# pns_client.py and pns_articulator.py, but without one level of articulation
# as it is just a sound base for a DNS peer with a cache, not a multiplexer.
#
# The final purpose is to provide HTTP and SMTP clients with a DNS interface,
# then to build a DNS/PNS gateway that provides DNS *and* PNS resolution to 
# other applications than Allegra's PRESTo web peer.
#
# This DNS client may cache responses but not requests: two distinct clients 
# "speaking-over" each other will not see their requests chained. TCP and UDP
# clients should hold a cache of named channels, and they therefore do not 
# require such feature from a DNS resolver.
# 
# One thing specific to DNS is the need for "fail-over" servers and "retry". 
#
# DNS is broken, so every request that times-out is sent to the next of the 
# request's asigned dns_servers (usually at the class level, by the module 
# loader), one or more times.
#
#
# Caveat!
#
# The UID used by this client are predictable. A clever attacker may flood
# it with probable sequences of UID and try to poison it. Or choose an even
# worse DNS relay as a media for his attack. What no attacker can do is
# escape the audit of unsollicited responses, wich of course undermine the
# credibility of an answer. DNS is not supposed to produce dissent. Any
# name about which there is dissent is not safe for public use.
#
