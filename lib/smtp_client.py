# Copyright (C) 2006 Laurent A.V. Szyster
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

from allegra import (
        loginfo, finalization, async_chat, producer, async_client,
        dns_client, tcp_client, mime_headers, mime_reactor
        )


HOSTNAME = socket.gethostname ()

SMTP_RESPONSE_INFO = frozenset ((
        '211', #System status, or system help reply'
        '214', #Help message
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


class Reactor (finalization.Finalization):

        def __init__ (self, mail_from, rcpt_to, body, headers=None):
                self.smtp_when = time.time ()
                self.smtp_mail_from = mail_from
                self.smtp_rcpt_to = rcpt_to[:]
                self.producer_body = body
                self.producer_headers = {
                        'Message-id': '<%f.%d@%s>' % (
                                self.smtp_when, id (self), HOSTNAME
                                ),
                        'Date': '%s %s' % (
                                time.asctime (time.gmtime (self.smtp_when)),
                                time.timezone
                                ),
                        'From': mail_from,
                        'To': ', '.join (rcpt_to)
                        }
                if headers: self.producer_headers.update (headers)
                self.smtp_responses = []


class Pipeline (async_chat.Dispatcher, async_client.Pipeline):
        
        # This SMTP client waits for 220 to wake up the pipeline, then uses 
        # the RSET command after each request is completed, in effect leaving
        # up to the SMTP server to "pull" reactors from the client's requests 
        # queue. Waking up the pipeline is simply done by sending NOOP.

        def __init__ (self):
                self.smtp_response = ''
                self.pipeline_set ()
                async_chat.Dispatcher.__init__ (self)
                self.set_terminator ('\r\n')

        def __repr__ (self):
                return 'smtp-client-pipeline id="%x"' % id (self)
        
        def __call__ (self, *args, **kwargs):
                req = Reactor (*args, **kwargs)
                self.pipeline_requests.append (req)
                return req

        def handle_connect (self): 
                pass
                
        def handle_close (self): 
                self.close ()
                
        def collect_incoming_data (self, data):
                self.smtp_response += data

        def found_terminator (self):
                if self.smtp_response[3] == '-':
                        # rest of a multi-line response, drop it!
                        self.smtp_response = ''
                        return
                
                response = self.smtp_response[:3]
                self.smtp_response = ''
                if not response in SMTP_RESPONSE_CONTINUE:
                        if response in SMTP_RESPONSE_CLOSE:
                                self.handle_close ()
                                return True
                        
                        elif response in SMTP_RESPONSE_ABORT:
                                self.pipeline_responses.popleft ()
                        return
                        
                if response == '220':
                        self.output_fifo.append ('HELO %s\r\n' % HOSTNAME)
                        return
                
                if not self.pipeline_responses:
                        # no response expected. if there is a pending reactor,
                        # pipelined pop it from the requests queue, send MAIL 
                        # FROM command and push the reactor on the responses 
                        # queue. otherwise keep the connection alive or QUIT.
                        #
                        if self.pipeline_requests:
                                reactor = self.pipeline_requests.popleft ()
                                self.output_fifo.append (
                                        'MAIL FROM: <%s>\r\n'
                                        '' % reactor.smtp_mail_from
                                        )
                                reactor.smtp_recipient = 0
                                self.pipeline_responses.append (reactor)
                        elif not self.pipeline_keep_alive:
                                self.output_fifo.append ('QUIT\r\n')
                                self.output_fifo.append (None)
                        return
                
                # response expected ...
                reactor = self.pipeline_responses[0]
                if reactor.smtp_rcpt_to:
                        # RCPT TO command for next recipient
                        self.output_fifo.append (
                                'RCPT TO: <%s>\r\n'
                                '' % reactor.smtp_rcpt_to.pop (0)
                                )
                elif reactor.smtp_responses[-1] != '354':
                        # send DATA command or mail input
                        if response == '354':
                                push = self.output_fifo.append 
                                # start mail input, end with <CRLF>.<CRLF>
                                push (''.join (mime_headers.lines (
                                        reactor.producer_headers
                                        )))
                                push (mime_reactor.Escaping_producer (
                                        reactor.producer_body
                                        ))
                                push ('\r\n.\r\n')
                                self.handle_write ()
                        else:
                                self.output_fifo.append ('DATA\r\n')
                else:
                        # reactor completed, 
                        self.pipeline_responses.popleft ()
                        self.output_fifo.append ('RSET\r\n')
                reactor.smtp_responses.append (response)
                
        def pipeline_wake_up (self):
                self.output_fifo.append ('NOOP\r\n')
        
        
def connect (domain):
        dispatcher = Pipeline ()
        def resolve (request):
                if not request.dns_resources:
                        return 
                
                dispatcher.mx_records = request.dns_resources[:] # copy!
                tcp_client.connect (
                        dispatcher, (dispatcher.mx_records.pop (0), 25)
                        )
                                                
        dns_client.lookup ((domain, 'MX'), resolve)
        return dispatcher
  

def try_next_mx (dispatcher):
        if not (dispatcher.connected or dispatcher.closing):
                if tcp_client.connect (
                        dispatcher, (dispatcher.mx_records.pop (0), 25)
                        ):
                        dispatcher.finalization = try_next_mx (d)
                        

def mailto (mail_from, rcpt_to, body, headers=None, continuation=None):
        domains = {}
        for address in rcpt_to:
                domains.setdefault (
                        address.split ('@', 1)[1], []
                        ).append (address)
        if len (domains) == 1:
                connect (domains.keys ()[0]) (
                        mail_from, rcpt_to, body, headers
                        ).finalization = continuation
                return
        
        for domain, rcpt_to in domains.items ():
                connect (domain) (
                        mail_from, rcpt_to, producer.Tee (body), headers
                        ).finalization = continuation