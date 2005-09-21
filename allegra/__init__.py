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

"http://laurentszyster.be/blog/allegra/"

__author__ = "Laurent A.V. Szyster <contact@laurentszyster.be>"

# Table of Content

__all__ = [

        # Introduction

        # 'async_core', 'async_chat', 
        
        # Part I - Asynchronous Internet Peer, with Safe Threading
        
        'loginfo', 'async_loop', 'finalization', 'fifo', 
        'select_trigger', 'thread_loop', 'sync_stdio', 'synchronizer',
        'timeouts', 'async_limits', 'udp_peer', 'tcp_client', 'tcp_server', 
        'collector', 'producer', 'reactor', 'netstring', 
        
        # Part II - The Usual Suspects, Internet Application Protocols
        
        'xml_dom','xml_unicode', 'xml_utf8', 'xml_producer', 
        'mime_collector', 'mime_producer', 'http_collector', 
        'http_server', # 'smtp_server', 'pop_server', 'nnrp_server',
        # 'dns_client', 'dns_cache', 'dns_resolver',
        # 'http_client', 'smtp_client', 'pop_client', 'nnrp_client', 
        
        # Part III - PNS, The Semantic Peer
        
        'pns_model', 'pns_persistence', 'pns_semantic', 
        'pns_peer', 'pns_tcp', # 'pns_udp',
        'pns_client', 'pns_articulator', 
        
        # Part IV - PRESTo, The Web Peer
        
        'presto', 'presto_http', 'presto_prompt', 'presto_bsddb', 
        
        # Part VI - PNS Application Test Cases.

        'pns_sat', 'pns_xml', 'pns_rss', #'pns_html',
        
        # Part VI - The Last DNS Application.

        # 'dns_pns'
        
        ]
        
        
# Note about This Implementation
#
#
# PNS Developper ToolKit
#
# Allegra, the library, can be applied to something else than the Semantic
# Web Peer. First and foremost, it is a reference implementation of PNS and
# it should provides a practical toolkit for PNS developpers.
#
# Most modules include a script that is their "primary" application, 
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
# Like all carpenters, tailors and shoemakers use to say:
#
#  "Measure twice, cut once."
#
# This is why Allegra comes with more than one test case for each aspect
# of its API.
#
