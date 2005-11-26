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

"http://laurentszyster.be/blog/pns-model/"

import re

from allegra import netstring


NETSTRING_RE = re.compile ('[1-9][0-9]*:')

def pns_name_clean (name):
        # scan the beginning of a potential "stealth" netstrings and check
        # their length. Upon discovery, return '' as the public name.
        # This adds a regexp match to validate public names, but there is no
        # other way to protect fast search of a public names string against
        # such evil scheme ... or blunder.
        #
        s = NETSTRING_RE.search (name)
        while s:
                end = s.end () + int (s.group ()[:-1])
                if end < len (name) and name[end] == ',':
                        return False
                        
                s = NETSTRING_RE.search (name, s.end ())
        return True
        
        
def pns_name (encoded, horizon, HORIZON=126):
        # Recursively validate a Public Name, returns the empty string if
        # the name encoded is invalid or inside the horizon. This function
        # does more than just assert that the encoded 8-bit byte string is
        # a valid public name: it transform it to a valid public name.
        #
        # try to decode the articulated public names
        names = [n for n in netstrings.decode (encoded) if n]
        if not names:
                if encoded not in horizon and pns_name_clean (encoded):
                        # clean name new in this horizon
                        horizon.add (encoded)
                        return encoded
                        
                # unsafe 8-bit byte string or Public Name in the in horizon
                return ''

        # possibly a valid composed public name, must not be dispersed
        valid = []
        for name in names:
                # recursively validate each articulated name in this horizon
                name = pns_name (name, horizon, HORIZON)
                if name:
                        valid.append (name)
                        if len (horizon) >= HORIZON:
                                break
                                
        if len (valid) > 1:
                # sort articulated names and encode
                valid.sort ()
                return netstring.encode (valid)
                
        if len (valid) > 0:
                # return singleton as allready encoded
                return valid[0]
                
        return '' # nothing valid to articulate in this horizon


def pns_quatuor (encoded, pns_names, PNS_LENGTH=1024):
        # a valid quatuor must have subject, predicate, object and context
        #
        model = list (netstrings.decode (encoded))
        if len (model) != 4:
                return None, '1 not a quatuor'
        
        if model[3]:
                # Validate the context as a public name, but allways check
                # the supplied cache of valid PNS names first!
                #
                if not (
                        model[3] in pns_names or
                        model[3] == pns_name (model[3], set ())
                        ):
                        return None, '2 invalid context'
                        
        if model[0]:
                # the predicate length and subject length are limited to 
                # or 512 bytes minus the ten needed to encode them
                #
                sp_len = len (model[0]) + len (model[1]) + len (
                        '%d%d' % (len (model[0]), len (model[1]))
                        )
                if sp_len > PNS_LENGTH/2:
                        return None, '3 invalid statement length'

                # validate the statement subject as a public name
                if model[0] != model[3] and not (
                        model[0] in pns_names or
                        model[0] == pns_name (model[0], set ())
                        ):
                        return None, '4 invalid subject'
                        
                if model[2]:
                        # non-empty objects are trunked to fit the 1024 bytes
                        # PNS/UDP answer datagram. Sorry guys, but there is
                        # no way to fit more and rationning the number of
                        # statement per user *does* limit potential abuses.
                        #
                        model[2] = model[2][:(
                                PNS_LENGTH - sp_len - len (
                                        '%d' % (PNS_LENGTH - sp_len)
                                        )
                                )]
                        #
                        # this is not an error condition, its a welcome
                        # feature of any PNS peer, the only "optional"
                        # error handling that allows use agent to be sloppy
                        # in their validation of PNS statements. simplistic
                        # clients should be tolerated ;-)
        elif model[1]:
                if not (
                        model[1] in pns_names or
                        model[1] == pns_name (model[1], set ())
                        ):
                        return None, '5 invalid command predicate'
                           
        elif model[2] and not (
                model[2] in pns_names or
                model[2] == pns_name (model[2], set ())
                ):
                return None, '6 invalid command object'
                        
        return model, ''


def pns_quintet (model, direction):
        l = ['%d:%s,' % (len (s), s) for s in model[:4]]
        l.append ('%d:%s,' % (len (direction), direction))
        return ''.join (l)
        
        
if __name__ == '__main__':
        import sys, time
        assert None == sys.stderr.write (
                'Allegra PNS/Model Validation'
                ' - Copyright 2005 Laurent A.V. Szyster\n'
                )
        from exceptions import StopIteration
        def benchmark (t, c):
                t = (time.time () - t)
                sys.stderr.write ('\n\n%d in %f seconds (%f/sec)\n' % (
                        c, t, (c/t)
                        ))
        timer = time.time ()
        counter = 0
        pipe = netstrings.netpipe (lambda: sys.stdin.read (4096))
        while 1:
                try:
                        encoded = pipe.next ()
                        model, error = pns_quatuor (encoded, ())
                        counter += 1
                        if model:
                                sys.stdout.write (
                                        '%d:%s,' % (len (encoded), encoded)
                                        )
                        else:
                                sys.stderr.write (
                                        '%d:%s,' % (len (encoded), encoded)
                                        )
                                sys.stderr.write (
                                        '%d:%s,' % (len (error), error)
                                        )
                except StopIteration:
                        break

        assert None == benchmark (timer, counter)
        #
        # Validate a PNS/TCP session, valid goes to STDOUT, invalid to STDERR.
        #
        # use -OO to prevent benchmark


# Note about this implementation
#        
# KISS!
#
# The PNS/Model is implemented as a simple sequence of strings.
#
# ['subject', 'predicate']
# ['subject', 'predicate', 'object']
# ['subject', 'predicate', 'object', 'name']
# ['subject', 'predicate', 'object', 'name', 'ip:port']
#
# where 'ip:port' is a PNS/TCP session text reference for the PNS peer.
#
# The whole Object shebang is not so nice, specially if this design was to be
# reimplemented as system pipes, a la DJB, passing netstrings between
# supervised and reliably logged queued processes and safe asynchronous
# network I/O. A simple string/list/tuple keeps you think on industrial
# strength simplicity of the protocol.
#
# A decoder function for PNS Contextual RDF Triples (pns_quatuor) and an
# encoder for directed quatuor (pns_quintet) will just do.
#
# Without much more than a lists and strings to instanciate for each
# statements, a PNS peer is lean on memory and CPU, even in Python. Once
# the functions below and above are optimized in a C module, this functional
# model would be quite fast too and still very much as pythonic at the next
# level of abstraction (where Python excels!).
#
# Note that the "original" model instanciated from asynchronous input is
# allways a list, but its copies handled by the threads are mostly tuples.
#
#
# Performances
#
# A C module for netstrings and public name validation will certainly improve
# performances of Allegra. Basically, those two functions are probably the one
# where the peer will spend the greater share if not most of its CPU time.
#
#
# Blurb: Python Rules!
#
# With Python it is possible to design large cross-plateform projects,
# then to reach a stable interface and implementation faster than with C.
# And yet be able# to reuse countless C libs or optimize to a C module later.
#
# Allegra *is* such a projet (on a individual scale, myself ;-) and I could
# not have made it without Python 2.4, sets types, C heap queue, bsddb or
# expat bindings and standard distribution. Compared to Java or C#, Python
# offers a narrower set of practical solutions, the one selected by its
# community. One database C library (BSDDB). One XML C library (Expat and its
# cElementTree sibbling). One Object Database C library (cPickle) and
# interface (ZODB). Peer review tend to elect a few standard implementation,
# possibly one for common functions. 
