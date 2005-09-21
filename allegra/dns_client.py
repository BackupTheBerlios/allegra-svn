""

# TODO: handle PTR right, handle non-existing domain/host and other
#        DNS error conditions, change the DNS predicates to QCLASS
#        and QTYPE values ...

import os
import time

from allegra.loginfo import Loginfo
from allegra.finalization import Finalization, finalization_extend
from allegra.udp_channel import UDP_dispatcher

# a bit of OS specific code to get the addresses of the DNS name
# servers for each plateform. this is a quick hack for NT only
# at the moment.
#
# TODO: parse etc/resolve.conf on UN*X, get MacOS data, etc

if os.name == 'nt':
    
        import re

        def dns_client_servers_get ():
                # parse "ipconfig /all", works on Windows 2000 but
                # should access the Win32 registery instead
                m = re.search (
                        'DNS Servers.+?'
                        '([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+).+?'
                        '([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)',
                        os.popen('ipconfig /all','r').read (),
                        flags=re.DOTALL
                        )
                if m:
                        return m.groups ()
                    
                else:
                        raise Error (
                                'Could not extract the ip addresses from the output '
                                'of "IPCONFIG /ALL"'
                                )
                    
else:
        def dns_client_servers_get ():
                return []


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

class DNS_datagram (Finalization):

        dns_question = None
        dns_when = 0
        dns_ttl = None

        dns_servers = ['127.0.0.1']
        dns_failover = 0
        dns_uid = None
        dns_peer = None
        dns_response = None
        dns_resources = None

        def __init__ (self, subject):
                self.dns_subject = subject

        def __repr__ (self):
                if not self.dns_resources:
                        return ('<dns-datagram ttl="%d"><![CDATA[%s]]!>' % (
                                        self.dns_ttl, self.dns_question
                                        ))

                return ('<dns-datagram ttl="%d"><![CDATA[%s%d:%s]]!>' % (
                                self.dns_ttl,
                                self.rdf_netstrings (),
                                netstrings_encode (self.dns_resources)
                                ))
                                
        def udp_datagram (self):
                return (
                        self.DNS_DATAGRAM % (
                                chr ((self.dns_uid>>8)&0xff),
                                chr (self.dns_uid&0xff),
                                ''.join ([
                                        '%c%s' % (chr (len (part)), part)
                                        for part in self.dns_subject.split ('.')
                                        ])
                                )
                        )

        def dns_unpack (self, datagram):
                self.dns_response = datagram
                ancount = (ord (datagram[6])<<8) + (ord (datagram[7]))
                # skip question, first name starts at 12, this is followed by QTYPE
                # and QCLASS
                if ancount:
                        pos = dns_skip_name (datagram, 12) + 4
                        self.dns_resources = []
                        # we are looking very specifically for one TYPE and one CLASS
                        for an in range (ancount):
                                pos = dns_skip_name (datagram, pos)
                                if self.dns_unpack_continue (datagram, pos):
                                        break
                                        
                                # skip over TYPE, CLASS, TTL, RDLENGTH, RDATA
                                pos += 8
                                pos += 2 + (ord (datagram[pos])<<8) + (ord (datagram[pos+1]))
                        return self.dns_unpack_end ()

                return 0 # error

        def dns_unpack_continue (self, datagram, pos):
                raise Error (
                        '%s.dns_resource not implemented' % self.__class__.__name__
                        )

        def dns_unpack_end (self):
                return 1


class DNS_A_datagram (DNS_datagram):

        rdf_predicate = 'dns:A'

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
                        return 1

                return 0
        

class DNS_PTR_datagram (DNS_datagram):

        rdf_predicate = 'dns:PTR'

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
                        return 1

                return 0


class DNS_NS_datagram (DNS_datagram):

        rdf_predicate = 'dns:NS'

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
                return 0

        def dns_unpack_end (self):
                if self.dns_resources:
                        self.dns_resources.sort ()
                        self.dns_ttl = min (
                                [rr[0] for rr in self.dns_resources]
                                )
                        return 1

                return 0


class DNS_MX_datagram (DNS_datagram):

        rdf_predicate = 'dns:MX'

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
                return 0
                
        def dns_unpack__end (self):
                if self.dns_resources:
                        self.dns_resources.sort ()
                        self.dns_ttl = min ([rr[2] for rr in self.dns_resources])
                        return 1

                return 0


DNS_datagrams = {
        'A': DNS_A_datagram,
        'PTR': DNS_PTR_datagram,
        'MX': DNS_MX_datagram,
        'NS': DNS_NS_datagram
        }


class DNS_client (UDP_dispatcher):

        dns_timeout = 3

        def __init__ (self, servers=None):
                self.dns_client_sent = 0
                self.dns_client_pending = {}
                self.dns_client_cache = {}
                UDP_dispatcher.__init__ (self)
                self.udp_bind ('')

        def __repr__ (self):
                return '<dns-client pending="%d" sent="%d"/>' % (
                        len (self.dns_client_pending),
                        self.dns_client_sent
                        )

        def dns_resolve (self, subject, predicate, resolve):
                assert DNS_datagrams.has_key (predicate)
                question = (subject, predicate)
                dns_request = self.dns_cache.get (question)
                if dns_request != None and dns_request[0] < time.time ():
                        resolve (dns_request)
                        return
                                
                dns_request = DNS_datagrams[predicate] (subject)
                dns_request.dns_question = question
                dns_request.dns_uid = self.dns_client_sent % (1<<16)
                dns_request.dns_peer = (dns_request.dns_servers[0], 53)
                dns_request.finalization = resolve
                self.dns_client_pending [dns_request.dns_uid] = dns_request
                self.sendto (dns_request.udp_datagram (), peer)
                self.dns_client_sent += 1

        def handle_read (self):
                datagram, peer = self.recvfrom (512)
                uid = (ord (datagram[0]) << 8) + ord (datagram[1])
                dns_request = self.dns_client_pending.pop (uid)
                if dns_request == None or dns_request.dns_peer != peer:
                        self.log (
                                '<dns-unsolicitted'
                                ' ip="%s" port="%d"'
                                ' />' % peer, ''
                                )
                        return
                        
                # consider the DNS request as answered, 
                # unpack, cache and finalize
                self.dns_cache[dns_request.dns_key] = (
                        dns_request.dns_ttl+time.time (), 
                        dns_request.dns_resources
                        )

        def timeouts_timeout (self, collected, period):
                for key in collected:
                        finalized = self.dns_cache[key]
                        if finalized.dns_ttl == None:
                                del self.dns_client_pending[finalized.dns_uid]
                        finalized.dns_failover += 1
                        if finalized.dns_failover < (
                                len (finalized.dns_servers) * self.dns_failover
                                ):
                                finalized.dns_peer = (
                                        finalized.dns_servers[
                                                request.dns_failover % len (
                                                        request.dns_servers
                                                        )
                                                ], 53
                                        )
                                self.sendto (finalized.udp_datagram (), finalized.dns_peer)
                        else:
                                finalized.dns_ttl = self.dns_ttl
                                finalized.finalization (finalized)
                                finalized.finalization = None


# Note about this implementation
#
# Allegra's DNS client is designed to provide a cache and support recursive
# domain name resolution or domain MX lookup. Its design is heavily inspired
# from pns_client.py and pns_articulator.py, and it is a sound base for a
# DNS peer.
#
# However, there is no real need for a multiplexer. The client may cache
# responses but not requests: two distinct clients "speaking-over" each
# other will not see their requests chained, .
#
# The purpose is to provide HTTP and SMTP clients with a DNS interface, then
# to build a DNS/PNS gateway that provides DNS *and* PNS resolution to other
# applications than Allegra's PRESTo web peer.
