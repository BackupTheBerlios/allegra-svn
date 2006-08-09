from allegra import loginfo, ip_peer
        
s = ip_peer.host_ip
loginfo.log ('%r' % ip_peer.is_ip (s))
loginfo.log ('%r' % s)
l = ip_peer.ip2long (s)
loginfo.log ('%r' % l)
loginfo.log ('%r' % (ip_peer.long2ip (l)))
loginfo.log ('%r' % ip_peer.in_addr_arpa (s))
loginfo.log ('%r' % ip_peer.is_local (l))
loginfo.log ('%r' % ip_peer.is_private (l))

