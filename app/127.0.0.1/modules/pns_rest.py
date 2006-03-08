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

from allegra import (
        netstring, loginfo, finalization, producer, 
        pns_sat, pns_xml, pns_articulator,
        presto_pns, presto_http
        )


# PNS/REST Articulator

def pns_articulate_rest (finalized):
        "generates the REST for the finalized articulation"
        yield '<presto:pns-articulate>'

        if finalized.pns_index:
                yield pns_xml.public_unicode (
                        finalized.pns_index, 'presto:pns-index'
                        )
                        
        for subject, statements in finalized.pns_subjects:
                yield '<presto:pns-subject>'
        
                yield pns_xml.public_unicode (subject, 'presto:pns-index')
        
                for model in statements:
                        yield pns_xml.pns_xml_unicode (
                                model, pns_xml.pns_cdata_unicode (model[2])
                                )
                                
                yield '</presto:pns-subject>'
        
        if len (finalized.pns_contexts) > 0:
                for name in finalized.pns_contexts:
                        yield pns_xml.pns_names_unicode (
                                name, 'presto:pns-context'
                                )
                
        if len (finalized.pns_sat) > 0:
                for model in finalized.pns_sat:
                        yield pns_xml.pns_xml_unicode (
                                model, pns_xml.pns_cdata_unicode (model[2])
                                )
                                
        yield '</presto:pns-articulate>'
                        
                        
class PNS_articulate (producer.Stalled_generator):
        
        "the articulation's finalization"
        
        def __call__ (self, finalized):
                self.generator = pns_articulate_rest (finalized)
                                

def pns_articulate (component, reactor):
        "articulate a context"
        if not reactor.presto_vector:
                return '<presto:pns-articulate/>'
        
        if component.pns_client == None:
                if component.pns_open (reactor):
                        component.pns_articulator = PNS_articulator (
                                component.pns_client
                                )
                else:
                        return '<presto:pns-tcp-error/>'
                
        text = reactor.presto_vector.get (u'articulated', u'').encode ('UTF-8')
        if not text:
                return '<presto:pns-articulate/>'
        
        lang = reactor.presto_vector.get (u'lang')
        if lang:
                component.pns_sat_language = pns_sat.language (
                        lang.encode ('UTF-8')
                        )
        articulated = []
        name = pns_sat.articulate_re (
                text, articulated.append, component.pns_sat_language
                )
        if not name:
                return '<presto:pns-articulate/>'

        react = PNS_articulate ()
        pns_articulator.PNS_articulate (
                component.pns_articulator, name, netstring.netlist (
                        reactor.presto_vector[
                                u'predicates'
                                ].encode ('UTF-8') or 'sat'
                        )
                ).finalization = react
        return react
        

def pns_articulate_new (component, reactor):
        "clear the articulator's cache, if any"
        articulator = component.pns_articulator
        if articulator != None:
                articulator.pns_commands = {}
                articulator.pns_commands = {}
        return '<presto:pns-articulate-new/>'


# PRESTo Component Declaration

class PNS_REST (presto_pns.PNS_session):

        xml_name = u'http://allegra/ pns-rest'
        
        presto = presto_http.get_rest
                        
        presto_interfaces = set ((
                u'PRESTo', 
                u'subject', u'predicate', u'object', u'context',
                u'context', u'text'
                ))

        presto_methods = {
                None: presto_pns.pns_statement,
                u'articulate': pns_articulate,
                u'clear': pns_articulate_new,
                }


presto_components = (PNS_REST, )

if __debug__:
        from allegra.presto_prompt import presto_debug_async
        presto_debug_async (PNS_REST)
        

# Roadmap
#
# PRESTo/PNS is an application of PNS/XML shrinkwrapped as a multi-purpose
# component, programmable with XSLT and themable with CSS. It is the same
# one used for the web test cases of PNS/SAT, PNS/XML and PNS/RSS, only 
# stylesheets and XML component instances are different.
#
# PNS/REST is PNS/REST is PNS/REST.
#
#
# The "default" method is a pass-through interface to a PNS/TCP session
# managed by the PNS_client instanciated for all PNS_session instances
#
#        GET ?subject=&predicate=&object=&context
#
# yields a PNS/XML response in a PRESTo envelope.
#
# Another RESTfull interface is provided by:
#
#        GET ?PRESTo=articulate&context=
#        GET ?PRESTo=articulate&context=&text=
#
# The AJAX-ready counterparts of the interface above:
#
#        GET /pns?subject=&predicate=&object=&context
#        GET /articulate?context=
#        GET /articulate?context=&text=
#
# produce an envelope-less response, just the REST expected by a statefull
# client that does not need a copy of the instance method state. This may
# save a significant amount of resources dedicated to the serialization
# of that state by the peer and the equivalent bandwith used.
#
#
# Synopsis
#
# <presto:pns 
#        xmlns:presto="http://presto/"
#        metabase="127.0.0.1:3534" 
#        language="en"
#        >
#        <presto:subscription pns=""/>
# </presto:pns>
#
# ?object=
#
# <presto:pns-index/>
#
# ?predicate=
#
# <presto:pns-context/>
#
# ?predicate=&object=
#
# <presto:pns-route/>
#   <presto:pns-context/><presto:pns-index/>
# </presto:pns-route>
#
# ?subject&=predicate=&object=&context=
#
        
"""

<allegra:pns-sat xmlns:allegra="http://allegra/"
  metabase="127.0.0.1:3534" 
  language="en"
  />


The PNS/SAT textpad is a simple prototype of an articulator:
        
        context: 
        subject: 
                
With only the two fields above and a simple dialog:
        
        1. if there is an articulated SAT subject, make one or more
           statements about that subject and articulate the echo of
           those statements. for practical reasons, a block pad is
           limited to short messages of 10 lines of 72 characters,
           big enough for most e-mail, SMS, etc ... and an HTTP GET ;-)
        
        2. if there is no subject, search for any subject in the context
           articulated, display them and let the user articulate their
           next subject using the names of the subjects and contexts
           collected.
           
        3. if there are no subjects found by the context graph search
           display the options of posting a new subject.

The same intuitive interface is common to the PNS/XML metapad, the PNS/RSS 
blogpad and its last sibbling the PNS/XHTML webpad.

Reuse, reuse, reuse.

Because, in effect, it will be the same thing through anyway. Where PNS/XML
greatly differ is in the ability to articulate long documents with many 
levels of details, but fundamentally the UI must stay consistent. There is
a bit of evil in that Allegra enforce a simple user experience that is hard
to embrace and extend. I don't see any significant improvement over the
generic semantic walk implemented by pns_articulator.py (whatever the outcome
on pns_inference.py, the direction of sorting is a reversible decision ;-)

Basically, this is what we do when searching. These are the three states:
        
        Statement
        
        Question and Answers
        
        Continue to articulate ...

Allegra's web application don't (can't and should not) hide the dialog
that takes places with the PNS metabase. They augment it, they articulate
it further for the user, so that he does not have to "speak" volumes and
may "click" his words through when browsing his own information network.

And articulate. Seach "semantically fast" in your own words. 

Naturally and individually.

Use your left brain and let your machine flex its right muscle ;-)

"""

                