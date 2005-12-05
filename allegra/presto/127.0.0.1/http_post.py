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

from allegra import presto, presto_http


class PRESTo_form (presto.PRESTo_async):
        
        xml_name = u'http://test/ form'

        def presto (self, reactor):
                if presto_http.presto_form (reactor):
                        return '<http-post/>'
        
                return reactor.presto_vector
                
# The rational is that the PRESTo handler leaves the choice and
# responsability of the MIME body collector to the instance's
# method called. So that components can themselves pick up from
# a variety of protocols like SOAP or XML/RPC, without making
# PRESTo's HTTP handler more complex.
#
# The benefit for applications developpers is the ability to
# control effectively how input is collected and process data as 
# it is collected. Validating, transcoding and parsing data can be 
# integrated differently and optimaly for each method, and each of
# these high-profile processes may them be optimized individually
# if they are not allready by Python's builtins.
#
# Beyond support for all kind of RPC scheme developped on top of 
# HTTP it effectively matters that a POST, PRESTo's way to handle
# collected MIME bodies also provides Web media developpers with
# a practical interface.
#
# Lets take the example of a Multipart MIME file upload. Its body
# aggregates encoded form data for the POST request as well as one
# or more parts. Now suppose that one or all of those parts must be
# processed asap, for instance to check an MPEG video header and
# validate the attached XML description and set a low limit to the
# parts size *before* waisting 300MB of bandwith and half and hour
# of everybody's time!
#
# Practically, by default a PRESTo HTTP peer drops any POST request
# and close the session when this interface is accessed but not
# implemented. Allegra provides a simple collector for URL encoded
# REST request, it is up to developpers to provide their own.