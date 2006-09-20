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

"http://laurentszyster.be/blog/public_rdf/"

from allegra import netstring, public_names


def pns_triple (model, max=1024):
        "validate the length of a triple as fitting a PNS/UDP datagram"
        assert model[0] and type (max) == int and max % 2 == 0
        sp_len = len (model[0]) + len (model[1]) + len (
                '%d%d' % (len (model[0]), len (model[1]))
                )
        if sp_len > max/2:
                return model, '3 invalid statement length %d' % sp_len

        if model[2]:
                model = (model[0], model[1], model[2][:(
                        max - sp_len - len ('%d' % (max - sp_len))
                        )], model[3])
        return model, ''


def pns_quatuor (encoded, contexts, max=1024):
        # a valid quatuor must have subject, predicate, object and context
        #
        assert type (max) == int and max % 2 == 0
        model = list (netstring.decode (encoded))
        if len (model) != 4:
                return None, '1 not a quatuor'
        
        if model[3]:
                # Validate the context as a public name, but allways check
                # the supplied cache of valid PNS names first!
                #
                if public_names.valid_as (model[3], contexts) != None:
                        return None, '2 invalid context'
                        
                
        if model[0]:
                # the predicate length and subject length are limited to 
                # or 512 bytes minus the ten needed to encode them
                #
                sp_len = len (model[0]) + len (model[1]) + len (
                        '%d%d' % (len (model[0]), len (model[1]))
                        )
                if sp_len > max/2:
                        return None, '3 invalid statement length'

                # validate the statement subject as a public name
                if model[0] != model[3] and public_names.valid_in (
                        subject, contexts
                        ) == None:
                        return None, '4 invalid subject'
                        
                if model[2]:
                        # non-empty objects are trunked to fit the 1024 bytes
                        # PNS/UDP answer datagram. Sorry guys, but there is
                        # no way to fit more and rationning the number of
                        # statement per user *does* limit potential abuses.
                        #
                        model[2] = model[2][:(
                                max - sp_len - len ('%d' % (max - sp_len))
                                )]
                        #
                        # this is not an error condition, its a welcome
                        # feature of any PNS peer, the only "optional"
                        # error handling that allows use agent to be sloppy
                        # in their validation of PNS statements. simplistic
                        # clients should be tolerated ;-)
        elif model[1]:
                if public_names.valid_in (command, contexts) == None:
                        return None, '5 invalid command predicate'
                           
        elif model[2] and public_names.valid_in (model[2], contexts) == None:
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
                'Allegra Public RDF'
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

