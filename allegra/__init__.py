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

__all__ = [

        # Introduction

        # 'async_core', 'async_chat', 
        
        # Part I - Asynchronous IP Peer
        
        'loginfo', 'async_loop', 'finalization', 'fifo', 
        'select_trigger', 'thread_loop', 'sync_stdio', 'synchronizer',
        'timeouts', 'async_limits', 'udp_peer', 'tcp_client', 'tcp_server', 
        'collector', 'producer', 'reactor', 'netstring', 
        
        # Part II - Internet Protocols
        
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
        
        # Part VI - PNS Applications.

        'pns_sat', 'pns_xml', 'pns_rss', #'pns_html',
        
        # Part VI - The Last DNS Application.

        # 'dns_pns'
        
        ]