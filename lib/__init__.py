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

__all__ = [
        #
        # Asynchronous Internet Peer
        #
        'netstring', 'prompt', 'loginfo', 
        'async_loop', 'finalization', 'async_core',
        'select_trigger', 'thread_loop', 'sync_stdio', 
        'async_net', 'async_chat', 'producer', 'collector', 'reactor', 
        'synchronized', 'async_limits', 'timeouts',
        'udp_peer', 'tcp_server', 'tcp_client', 
        #
        # Web Application Protocols
        #
        'dns_client', 'mime_headers', 'mime_reactor',
        # 'smtp_client', 'pop_client', 'nnrp_client', 
        'http_reactor', 'http_client', 'http_server', 
        'xml_dom', 'xml_unicode', 'xml_utf8', 'xml_reactor',
        #
        # PNS, The Reference Implementation
        #
        'sat', 'pns_model', 
        'pns_sat', 'pns_mime', 'pns_xml', 'pns_rss', # 'pns_html', 
        'pns_tcp', 'pns_resolution', 'pns_inference', 'pns_udp', 
        'pns_peer', 'pns_client', 'pns_articulator', 
        #
        # Allegra Presto
        #
        'presto', 'presto_http', 
        'presto_prompt', 'presto_pns', # 'presto_bsddb', 
        #
        # The Last DNS Application
        #
        # 'pns_dns'
        ]

__author__ = 'Laurent A.V. Szyster <contact@laurentszyster.be>'

# Roadmap
#
# This is a reference implementation. It is slow, unoptimized and possibly
# a little too "hacked". For instance, to use the Python Garbage Collector
# to turn finalization into cheap continuations is considered as a "hack",
# not "the right thing to do". But it does the job.
#
# The purpose of this library is to provide a "worse is better" solution
# in the short run, developped against a simple and effective model that
# may eventually mature as an industry-strength library, a standard API.
#
# Rewriting high-profile functions like netstring decoding and encoding, 
# Public Names validation or XML serialization is not a priority. Getting
# the Application Programming Interfaces (API) right is *the* first thing
# to do. Then only will it be fruitfull to optimize their implementation
# in hand crafted C code, full support for BSDDB fine tuning, etc.
#
#
# Like all carpenters, tailors and shoemakers use to say:
#
#  "Measure twice, cut once."
#
# So I tried to allways validating each API with at least two applications.
#
# The result is a practically orthogonal library. Allegra is successfully
# applied to develop such diverse software as an innovative metabase peer, 
# a powerfull HTTP/1.1 peer and semantic application components that 
# integrate multiprotocol asynchronous networking with synchronized system 
# and database functions.
#
# Modules in Allegra are designed as levers of the same magnitude in force
# and size (in numbers of lines), that are effectively applied to more 
# than one other module and/or application.
#        
#        
# Trading performance for scalability first
#
# As you will notice quickly, Allegra is still unoptimized. Several high
# profile functions are implemented in pure Python and contain CPU intensive
# loops. Yet, as a whole, Allegra provide a stable implementation which
# allready scales up to high-performances and high-reliability.
#
# The CPython optimization strategy has proved itself so profitable that its
# VM and standard C library bindings are available for a Nokia cell phone
# and IBM mini and mainframe systems. No other VM for a modern computer
# language has a wider or better cross-plateform API. And its mostly free
# with a gentle learning curve, a fast growing developper community and
# commercial support of better quality and lesser expenses than Microsoft's
# or Sun's Virtual Machines.
# 
# Allegra is designed along the lines of CPython's Zen, it is made to 
# integrate safely the C libraries of high profile functions for its
# applications.
#
# Leaving the complex and dynamic part of an application logic in Python
# delivers all the safety and reliability of CPython's industrial strength 
# interpreter. With the ability to implement quickly a better algorithm for 
# a complex process an application can be programmed to scale well first, 
# then be optimized latter, when its interfaces are stable. The end result
# is probably a lot better artefact than what could be programmed in the
# same amount of time in C or Java. It's first stable version may be two
# or three times slower than the following, it will scale up immediately.
