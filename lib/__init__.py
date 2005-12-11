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
        'select_trigger', 'thread_loop', 'sync_stdio', 'synchronizer', 
        'async_net', 'async_chat', 'async_limits', 
        'producer', 'collector', 'reactor', 
        'udp_peer', 'tcp_server', 'tcp_client', 
        #
        # Web Application Protocols
        #
        'dns_client', 'mime_headers', 'mime_reactor',
        # 'smtp_client', 'pop_client', 'nnrp_client', 
        # 'smtp_server', 'pop_server', 'nnrp_server', 
        'http_reactor', 'http_client', 'http_server', 
        'xml_dom', 'xml_unicode', 'xml_utf8', 'xml_reactor',
        #
        # PNS, The Reference Implementation
        #
        'pns_model', 'pns_sat', 'pns_xml', 'pns_mime',
        'pns_tcp', 'pns_resolution', 'pns_inference', 'pns_udp', 
        'pns_peer', 'pns_client', 'pns_articulator', 
        #
        # Allegra Presto
        #
        'presto', 'presto_http', # presto_smtp, presto_pop,
        'presto_prompt', 'presto_bsddb', 'presto_pns', 
        #
        # The Last DNS Application
        #
        # 'dns_peer'
        ]

__author__ = 'Laurent A.V. Szyster <contact@laurentszyster.be>'

# Note about This Implementation
#
#
# PNS Developper ToolKit
#
# Allegra, the library, can be applied to something else than the Semantic
# Web Peer. First and foremost, it is a reference implementation of PNS and
# it should provides a practical toolkit for PNS developpers.
#
# Many modules include a script that is their "primary" application, 
# their first practical application test cases. For instance you 
# can use the module that implements PNS/Model to validate a PNS/TCP
# session input or output:
#        
#   python -00 pns_model.py < input 1> valid 2> invalid
# 
# Other applications of the pns_model.py API are to be found in the various
# other pns_*.py modules of Allegra that implement PNS peer and user agents.
#
#
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
