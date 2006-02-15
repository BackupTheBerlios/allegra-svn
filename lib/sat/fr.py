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

"SAT/EN - Simple Articulated Text / English"

from allegra import sat

ARTICULATE = sat.ARTICULATE_ASCII_Head + (
        # Conjonctions de Subordination
        sat.articulators_re ((
                'comme', 'lorsque', 'puisque', 'quand', 'que', 'quoique', 'si'
                )),
        # Conjonctions de Coordination
        sat.articulators_re ((
                'mais', 'ou', 'et', 'donc', 'or', 'ni', 'car', 'cependant', 
                'néanmoins', 'toutefois',
                )),
        # Prépositions
        sat.articulators_re ((
                'devant', 'derrière', 'après', # le rang
                'dans', 'en', 'chez', 'sous', # le lieu
                'avant', 'après', 'depuis', 'pendant', # le temps
                'avec', 'selon', 'de', # la manière
                'vu', 'envers', 'pour', 'à', 'sans', 'sauf' # ? dispersés
                )),
        # Articles
        sat.articulators_re ((
                'un', 'une', 'des', 'le', 'la', 'les', 'du', 
                'de\\s+la', "de\\+l'",
                ))
        ) + sat.ARTICULATE_ASCII_Tail

