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

import socket, time

from allegra import \
        loginfo, finalization, async_chat, tcp_client, \
        dns_client, mime_headers, mime_reactor


HOSTNAME = socket.gethostname ()

SMTP_RESPONSE_INFO = frozenset ((
        '211', #System status, or system help reply'
        '214', #Help message
               #[Information on how to use the receiver or the meaning of a
               #particular non-standard command; this reply is useful only
               #to the human user]
        ))
        #
        # not used

SMTP_RESPONSE_CONTINUE = frozenset ((
        '220', #<domain> Service ready
        '250', #Requested mail action okay, completed
        '251', #User not local; will forward to <forward-path>
        '354', #Start mail input; end with <CRLF>.<CRLF>
        ))
        #
        # continue the protocol

SMTP_RESPONSE_ABORT = frozenset ((
        '450', #Requested mail action not taken: mailbox unavailable
               #[E.g., mailbox busy]
        '451', #Requested action aborted: local error in processing
        '452', #Requested action not taken: insufficient system storage
        '550', #Requested action not taken: mailbox unavailable
               #[E.g., mailbox not found, no access]
        '551', #User not local; please try <forward-path>
        '552', #Requested mail action aborted: exceeded storage allocation
        '553', #Requested action not taken: mailbox name not allowed
               #[E.g., mailbox syntax incorrect]
        '554', #Transaction failed
        ))
        #
        # abort the current request, RSET the protocol
         
SMTP_RESPONSE_CLOSE = frozenset ((
        '221', #<domain> Service closing transmission channel
        '421', #<domain> Service not available,
               #closing transmission channel
               #[This may be a reply to any command if the service knows it
               #must shut down]
        '500', #Syntax error, command unrecognized
               #[This may include errors such as command line too long]
        '501', #Syntax error in parameters or arguments
        '502', #Command not implemented
        '503', #Bad sequence of commands
        '504', #Command parameter not implemented
        ))
        #
        # This *is* a compliant SMTP implementation, if any of these 50X
        # errors should arise, the server *is* broken and the client must
        # close this unreliable pipeline.


class SMTP_client_reactor (finalization.Finalization):

        smtp_recipient = 0

        def __init__ (self, mail_from, rcpt_to, body, headers):
                self.smtp_when = time.time ()
                self.smtp_mail_from = mail_from
                self.smtp_rcpt_to = rcpt_to
                self.smtp_responses = []
                self.mime_producer_body = body
                self.mime_producer_headers = headers

        def more (self):
                if self.producer_stalled ():
                        return ''
                      
                if self.smtp_recipient < 0:
                        return '%s\r\n' % self.smtp_responses[-1]
                        
                self.smtp_recipient = -1
                return ''.join ([
                        '%s\r\n' % l for l in self.smtp_responses
                        ])
                
        def producer_stalled (self):
                return -1 < self.smtp_recipient < len (self.smtp_rcpt_to)


class SMTP_client_channel (
        tcp_client.Pipeline, tcp_client.TCP_client, async_chat.Async_chat, 
        ):

        "an SMTP client pipeline channel"
        
        # a simple implementation of an SMTP client pipeline.
        #
        # This SMTP client waits for 220 to wake up the pipeline, then uses 
        # the RSET command after each request is completed, in effect leaving
        # up to the SMTP server to "pull" reactors from the client's requests 
        # queue. Waking up the pipeline is simply done by sending NOOP.
        #
        # this is enough to support access to an outgoing SMTP relay

        def __init__ (self):
                self.smtp_response = ''
                tcp_client.Pipeline.__init__ (self)
                async_chat.Async_chat.__init__ (self)
                self.set_terminator ('\r\n')
                
        def collect_incoming_data (self, data):
                self.smtp_response += data

        def found_terminator (self):
                assert None == self.log (self.smtp_response, 'debug')
                response = self.smtp_response[:3]
                if not response in SMTP_RESPONSE_CONTINUE:
                        if response in SMTP_RESPONSE_CLOSE:
                                self.handle_close ()
                        elif response in SMTP_RESPONSE_ABORT:
                                self.pipeline_responses.popleft ()
                        return
                        
                if self.smtp_response[3] == '-':
                        # multi-line response, drop
                        self.smtp_response = ''
                        return
                        
                self.smtp_response = ''
                if not self.pipeline_responses:
                        # no response expected. if there is a pending reactor,
                        # pipelined pop it from the requests queue, send MAIL 
                        # FROM command and push the reactor on the responses 
                        # queue. otherwise keep the connection alive or QUIT.
                        #
                        if self.pipeline_requests:
                                reactor = self.pipeline_requests.popleft ()
                                self.push (
                                        'MAIL FROM: %s\r\n'
                                        '' % reactor.smtp_mail_from
                                        )
                                reactor.smtp_recipient = 0
                                self.pipeline_responses.append (reactor)
                        elif self.pipeline_keep_alive:
                                self.pipeline_sleeping = 1
                        else:
                                self.push ('QUIT\r\n')
                        return
                
                # response expected ...
                reactor = self.pipeline_responses[0]
                if reactor.smtp_recipient < len (reactor.smtp_rctp_to):
                        # RCPT TO command for next recipient
                        self.push (
                                'RCPT TO: %s\r\n'
                                '' % reactor.smtp_rcpt_to[
                                        reactor.smtp_recipient
                                        ]
                                )
                        reactor.smtp_recipient += 1
                elif reactor.smtp_responses[-1] != '354':
                        # send DATA command or mail input
                        if response == '354':
                                # start mail input, end with <CRLF>.<CRLF>
                                self.producer_fifo.append (''.join (
                                        mime_headers.lines (
                                                reactor.mime_producer_headers
                                                )
                                        ))
                                self.producer_fifo.append (
                                        mime_reactor.Escaping_producer (
                                                reactor.mime_producer_body
                                                )
                                        )
                                self.producer_fifo.append ('\r\n.\r\n')
                                self.handle_write ()
                        else:
                                self.push ('DATA\r\n')
                else:
                        # reactor completed, 
                        self.pipeline_responses.popleft ()
                        self.push ('RSET\r\n')
                reactor.smtp_responses.append (response)
                
        def pipeline_wake_up (self):
                self.push ('NOOP\r\n')


class SMTP_exchange_reactor (finalization.Finalization):
        
        def __init__ (
                self, mail_from, rcpt_to, body, headers=None
                ):
                # assert debug type check, complete headers if None specified,
                # index recipients per domain and send the body 
                #
                assert (
                        type (mail_from) == str and 
                        hasattr (rcpt_to, '__iter__') and
                        len (rcpt_to) == len ([
                                s for s in rcpt_to if type (s) == str
                                ]) and
                        hasattr (body, 'more') and
                        headers == None or type (headers) == dict
                        )
                if headers == None:
                        headers = {}
                        headers['message-id'] = '<%f.%d@%s>' % (
                               self.smtp_when, id (self), HOSTNAME
                               )
                        headers['date'] = '%s %s' % (
                               time.asctime (time.gmtime (self.smtp_when)),
                               time.timezone
                               )
                        headers['from'] = mail_from
                        headers['to'] = ',\r\n'.join (rcpt_to)
                # index recipient by domains name, use "127.0.0.1" as default
                recipients = {}
                for recipient in rcpt_to:
                        try:
                                domain = recipient.split ('@', 1)[1]
                        except:
                                domain = '127.0.0.1'
                        recipients.setdefault (domain, []).append (recipient)
                # instanciate one SMTP reactor per domain
                self.smtp_client_reactors = dict ([(domain, SMTP_reactor (
                        mail_from, recipients[domain], body, headers
                        )) for domain in recipients.keys ()])
                #for domain in recipients.keys ():
                #        client.tcp_client ((ip, 25), timeout).smtp_client (
                #                ).pipeline ()

        def __call__ (self, finalized):
                pass
                

class SMTP_client (dns_client.TCP_client_DNS):
        
        # manages a cache of one SMTP pipelines per server's IP address.
        
        TCP_CLIENT_CHANNEL = SMTP_client_channel
        
        def tcp_client_close (self, channel):
                TCP_client.tcp_client_close (self, channel)
                channel.pipeline_requests = channel.pipeline_responses = None
                
        def tcp_client_dns (self, channel, addr, resolved):
                if len (resolved.dns_resources) > 0:
                        # DNS address resolved, connect ...
                        channel.tcp_connect ((
                                resolved.dns_resources[0], addr[1]
                                ))
                else:
                        del self.tcp_client_channels[addr]
                        self.tcp_client_dns_error (channel, addr)
                

if __name__ == '__main__':
        pass
        #
        # pipe the content of a mailbox archive to the network ...
        
        
# Note about this implementation
#
# The purpose of this implementation is to provide a simple SMTP client 
# interface to send mail directly from a peer to the recipient's relay,
# bypassing the any forward queue and concurrently delivering mail to
# distinct mail exchanges.
#
# In effect Allegra's SMTP client will deliver much higher performance
# and reliability to its applications, simply because it sticks to the
# peer architecture supported by the protocol (which is why SMTP is such
# a slow cow when it comes to handle large message queues: it was never
# intended for such job).
#
# Synopsis
#
#        python -OO smtp_client.py sender, [recipients] < mailbox.txt
#
# API
#
#        python -OO sync_stdio.py -d
#
#        info
#        Allegra Console - ...
#
#        >>> from allegra import smtp_client
#        >>> smtp_client.SMTP_client_channel ((
#                '127.0.0.1', 25)).smtp_mailto (
#                'me@home', ('you@work', 'me@work')
#                ) (Simple_producer ('Subject: Test\r\n\r\nHello World?'))
#        >>>
#
# This module implements an SMTP client pipeline interface that will behave
# identically wether the server supports or not pipelining, that is without
# actually using ESMTP capabilities. Because the protocol syntax does not 
# allow true pipelining since each MAIL FROM and RCPT TO practically require
# the client to wait for an approval. If you *need* pipelining for obvious
# performance reasons, use DJBernstein amazing software and the QMTP or QMQP 
# protocols instead.
#
# This module is of course usefull only when relaying mail directly to
# the final recipients' relays, resolve their domain mail exchanges
# and relay one copy of the mail to the first available MX peer of
# each domain.
#
# The purpose of is to enable SMTP mail relay for a mobile peer, regardless 
# of the restrictions set by the outgoing relay(s) available where it is 
# connected. The benefit for its applications is the absence of configuration
# problems, the immediate error reporting, the increased confidentiality
# of the mail not relayed locally and probably better average delivery 
# performances for a peer thanks to distribution.
#
# Allegra is designed for peer networking, and in this case mail traffic
# will most probably be very "localized" and consist mainly of mails with 
# relatively few recipients belonging to fewer distinct domains. So, when 
# mail distribution is taken care at the peer itself, without relay, an
# absolute performance gain is made from the absence of latency induced by
# a central queue. And since what matters is the instant nature of messaging
# for a peer, the absence of fail-over retry made possible by that queue is
# not a missing function. Instead, the peer's user can immediately have an
# acknoledgement of delivery or a failure notice from which to respond.
# It is an ideal SMTP mail client for a personal network peer