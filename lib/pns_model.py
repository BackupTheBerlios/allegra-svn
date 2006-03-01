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
        names = [n for n in netstring.decode (encoded) if n]
        if not names:
                if encoded not in horizon and pns_name_clean (encoded):
                        # clean name new in this horizon
                        horizon.add (encoded)
                        return encoded
                        
                # unsafe 8-bit byte string or Public Name in the in horizon
                return ''

        # articulated Public Names
        valid = []
        for name in names:
                # recursively validate each articulated name in this horizon
                name = pns_name (name, horizon, HORIZON)
                if name:
                        valid.append (name)
                        if len (horizon) >= HORIZON:
                                break # but only under this HORIZON
                                
        if len (valid) > 1:
                # sort Public Names and encode
                valid.sort ()
                return netstring.encode (valid)
                
        if len (valid) > 0:
                # return a "singleton"
                return valid[0]
                
        return '' # nothing valid to articulate in this horizon


def pns_triple (model, PNS_LENGTH=1024):
        "validate the length of a triple as fitting a PNS/UDP datagram"
        assert model[0]
        sp_len = len (model[0]) + len (model[1]) + len (
                '%d%d' % (len (model[0]), len (model[1]))
                )
        if sp_len > PNS_LENGTH/2:
                return None, '3 invalid statement length %d' % sp_len

        if model[2]:
                model = (model[0], model[1], model[2][:(
                        PNS_LENGTH - sp_len - len (
                                '%d' % (PNS_LENGTH - sp_len)
                                )
                        )], model[3])
        return model, ''


def pns_quatuor (encoded, pns_names, PNS_LENGTH=1024):
        # a valid quatuor must have subject, predicate, object and context
        #
        model = list (netstring.decode (encoded))
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
        import sys, time, exceptions
        from allegra import loginfo
        assert None == loginfo.log (
                'Allegra PNS/Model Validation'
                ' - Copyright 2005 Laurent A.V. Szyster | Copyleft GPL 2.0', 
                'info'
                )
        def benchmark (t, c):
                t = (time.time () - t)
                loginfo.log (
                        'Validated %d statements in %f seconds'
                        ' (%f/sec)' % (c, t, (c/t)), 'info'
                        )
        timer = time.time ()
        counter = 0
        pipe = netstrings.netpipe (lambda: sys.stdin.read (4096))
        while True:
                try:
                        encoded = pipe.next ()
                except exceptions.StopIteration:
                        break

                model, error = pns_quatuor (encoded, ())
                counter += 1
                if model:
                        loginfo.log (encoded)
                else:
                        loginfo.log (encoded, error)
        assert None == benchmark (timer, counter)
        #
        # Validate a PNS/TCP session, valid goes to STDOUT, invalid to STDERR.
        #
        # use -OO to prevent benchmark


# Note about this implementation
#
# SYNOPSYS
#
#        >>> horizon = set ()
#        >>> pns_name ('8:1:Z,1:A,,12:1:B,1:B,1:C,,4:1:D,,', horizon)
#        '8:1:A,1:Z,,8:1:B,1:C,,1:D,'
#        >>> horizon
#        >>> set(['A', 'B', 'Z', 'C', 'D'])
#
# The pns_name function is the real magic behind PNS and Allegra. This
# apparently trivial piece of code has outstanding applications for
# computer networks. It can validate *and* map non-dispersed semantic
# graphs made of arbitrary articulations of 8-bit byte strings. Which
# means that it can be used to index any articulation in a network
# system that is infinitely diverse, yet dispersed in no given context.
#        
# If you don't understand the magnitude of the disruption made possible
# by Public Names applications, skip it alltogether and wait ... ;-)
#
# KISS!
#
# The rest of PNS/Model is implemented as a simple sequence of strings.
#
# ['subject', 'predicate']
# ['subject', 'predicate', 'object']
# ['subject', 'predicate', 'object', 'name']
# ['subject', 'predicate', 'object', 'name', 'ip:port']
#
# where 'ip:port' is a PNS/TCP session text reference for the PNS peer.
#
# The whole Object shebang is not so nice, specially if this design was to
# ever be reimplemented as system pipes, a la DJB, passing netstrings between
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
# Python Rules!
#
# With Python it is possible to design large cross-plateform projects,
# then reach a stable interface and implementation faster than with C.
#
# With very decent performances, thanks to countless fine C libs and the
# ability to spend more time on doing the right thing first.
#
# Optimizing a few high profile functions to a C module later is a sure
# bet, with CPython's VM sources and bindings at hand.
#
# Allegra is a projet I could not have completed without CPython 2.4, 
# sets types, C heap queue, bsddb or expat bindings and standard distribution.
# Compared to Java or C#, Python offers a narrower set of practical solutions,
# the one selected by its community. One database C library (BSDDB). One XML
# C library (Expat and its cElementTree sibbling). One Object Database C
# library (cPickle) and interface (ZODB).
#
# Peer review tend to elect a few standard implementation, possibly one for
# common functions. And it has been at work on the CPython VM and bindings
# for more years than C# or Java.
#
# Which means that as a developer I don't assume that my Python code is
# portable everywhere. I know it is, because the source code of the VM
# *is* of the same trunk and that it has been under a very long process
# of review by the worse bunch of all programmers, by mathematicians.
#
# I truly hope this module will make CPython the next Java-killer on the
# next generation of peer network devices. Although with CPython 2.2
# installing Windows XP Pro on a new Thinkpad and the same running
# mod_python on Nokia's OS, I'm not really taking any risks ;-)
# 
# CPython 2.4 is finally becoming mainstream.