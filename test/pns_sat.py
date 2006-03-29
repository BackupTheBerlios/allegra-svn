# -*- coding: CP1252 -*-

from allegra import netstring, loginfo, pns_sat

def log_articulated (articulated):
        for horizon, field, name, text in articulated:
                loginfo.log (text)
                loginfo.log (netstring.netoutline (name))

articulated = []
text = (
        'A just machine to make big decisions\n'
        'Programmed by fellows with compassion and vision'
        )
name = pns_sat.articulate_re (
        text, articulated.append, pns_sat.language ('en')
        )
log_articulated (articulated)

articulated = []
text = (
        "Ce qui se conçoit bien s'énonce clairement\n"
        "Et les mots pour le dire arrivent aisément"
        )
name = pns_sat.articulate_re (
        text, articulated.append, pns_sat.language ('fr')
        )
log_articulated (articulated)

articulated = []
text = (
        'This library is free software; you can redistribute it and/or '
        'modify it under the terms of version 2 of the GNU General Public '
        'License as published by the Free Software Foundation.'
        )
pns_sat.articulate_chunk (
        text, articulated.append, pns_sat.language ('en'), 72
        )
log_articulated (articulated)

text = (
        "Oh je voudrais tant que tu te souvienne "
        "Cette chanson était la tienne "
        "C'était ta préférée, je crois "
        "Qu'elle est de Prévert et Cosma"
        )
articulated_languages = pns_sat.articulate_languages (text, ('fr', 'en'))
loginfo.log ('%r' % (articulated_languages,))

