from allegra import netstring, pns_model

context = '7:Rushing,3:Sam,'
print context == pns_model.pns_name (context, set ())

context = '3:Sam,7:Rushing,'
print context == pns_model.pns_name (context, set ())

context = '4:Kill,4:Kill,8:Pussycat,'
print context == pns_model.pns_name (context, set ())

field = set ()
context = netstring.netstrings ((
        'An', 'example', 'of', (
                'Simple', 'Articulated', 'Text'
                ), 'and', 'a', 'bit', 'of', 'dispersion'
        ))
print netstring.netoutline (context)
name = pns_model.pns_name (context, field)
print netstring.netoutline (name)
print 'field: %r' % field
print 'horizon: %d' % len (field)