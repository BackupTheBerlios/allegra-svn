""

# TODO: handle PTR right, handle non-existing domain/host and other
#        DNS error conditions, change the DNS predicates to QCLASS
#        and QTYPE values ...

import time

from allegra import async_loop
from allegra.loginfo import Loginfo
from allegra.finalization import Finalization, finalization_extend
from allegra.udp_channel import UDP_dispatcher

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

class DNS_request (Finalization):

        dns_servers = ['127.0.0.1']
        dns_failover = 0

        dns_when = dns_uid = dns_peer = \
                dns_ttl = dns_response = dns_resources = None

        def __init__ (self, question):
                self.dns_question = question

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
                raise Error (
                        'The dns_unpack_continue is not implemented'
                        ' by the %s class.' % self.__class__.__name__
                        )

        def dns_unpack_end (self):
                return True

        def dns_timeout (self, when):
                try:
                        del self.dns_client.dns_pending[self.dns_uid]
                except KeyError:
                        return # ... allready answered, finalize ...
                        
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
                if self.dns_resources:
                        if len (self.dns_resources) > 1:
                                self.dns_resources.sort ()
                                if self.dns_resources[0][0] < self.dns_resources[-1][0]:
                                        self.dns_resources.reverse ()
                        self.dns_ttl = self.dns_resources[0][2]
                        self.dns_resources = tuple ([
                                rr[1] for rr in self.dns_resources 
                                ])
                        return True

                return False


DNS_requests = {
        'A': DNS_request_A,
        'PTR': DNS_request_PTR,
        'MX': DNS_request_MX,
        'NS': DNS_request_NS
        }


class DNS_client (UDP_dispatcher):

        udp_datagram_size = 512

        dns_timeout = 3

        def __init__ (self, ip=None):
                self.dns_sent = 0
                self.dns_pending = {}
                self.dns_cache = {}
                if ip == None:
                        import socket
                        ip = socket.gethostbyname (socket.gethostname ())
                UDP_dispatcher.__init__ (self, ip)

        def __repr__ (self):
                return '<dns-client pending="%d" sent="%d"/>' % (
                        len (self.dns_pending), self.dns_sent
                        )

        def dns_resolve (self, question, resolve):
                answer = self.dns_cache.get (question)
                when = time.time ()
                if answer != None and answer[0] < when:
                        resolve (answer)
                        return
                        
                request = DNS_requests[question[1]] (question)
                request.dns_client = self
                self.dns_send (request, when)
                request.finalization = resolve
                                
        def dns_send (self, request, when):
                request.dns_when = when
                request.dns_uid = self.dns_sent % (1<<16)
                request.dns_peer = (request.dns_servers[0], 53)
                self.dns_pending [request.dns_uid] = request
                self.sendto (request.udp_datagram (), request.dns_peer)
                async_loop.async_defer (
                        request.dns_when+self.dns_timeout,
                        request.dns_timeout
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
                if dns_request.dns_unpack (datagram):
                        self.dns_cache[dns_request.dns_question] = (
                                dns_request.dns_ttl + dns_request.dns_when, 
                                dns_request.dns_resources
                                )
                #
                # the dns_request instance will finalize, but only when it 
                # times out ...


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
                        raise Error (
                                'Could not extract the ip addresses from '
                                '"IPCONFIG /ALL"'
                                )
                    
        else:
                # TODO: parse /etc/resolve.conf for UNIX-like systems,
                #       suppose a simple dns local cache ...
                #
                return ['127.0.0.1']


if __name__ == '__main__':
        import sys
        assert None == sys.stderr.write (
                'Allegra DNS/UDP Client'
                ' - Copyright 2005 Laurent A.V. Szyster'
                ' | Copyleft GPL 2.0\n...\n'
                )
        from allegra.netstring import netstring_encode, netstrings_encode
        DNS_request.dns_servers = dns_servers ()
        def resolve (request):
                sp = netstrings_encode (request.dns_question)
                c = request.dns_peer[0]
                c = '%d:%s,' % (len (c), c)
                if request.dns_resources == None:
                        encoded = sp + '0:,' + c
                else:
                        encoded = netstrings_encode ([
                                sp + netstring_encode (res) + c
                                for res in request.dns_resources
                                ])
                sys.stdout.write (
                        '%d:%s,' % (len (encoded), encoded)
                        )
                sys.stderr.write ('\n')
        if len (sys.argv) > 1:
                if len (sys.argv) > 2:
                        if len (sys.argv) > 3:
                                DNS_request.dns_servers = sys.argv[3:]
                        DNS_client ().dns_resolve (
                                tuple (sys.argv[1:3]), resolve
                                )
                else:
                        DNS_client ().dns_resolve ((sys.argv[1],'A'), resolve)
        else:
                DNS_client ().dns_resolve (('localhost', 'A'), resolve)
        try:
                async_loop.loop ()
        except:
                async_loop.loginfo.loginfo_traceback ()
        
        
# Note about this implementation
#
# This is a very "strict" DNS client indeed, because it will wait all the
# timeout period set before finalization of the request instance it manages.
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
#
# A DNS Peer that is safe for public use
#
# A DNS/PNS gateway does just that: lookup DNS and PNS concurrently
# and wait until 3 seconds (the PNS timeout) before reporting a local
# answer witout DNS echo (safe), the same with a DNS confirmation, or
# a PNS update, or dissent. In any case of dissent, the first local
# answer or the PNS update will prevail.
#
# Practically a DNS/PNS peer is as safe for public use as DNS can get.
#
# 