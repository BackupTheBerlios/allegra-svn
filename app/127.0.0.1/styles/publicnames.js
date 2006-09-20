/* 

Copyright (C) 2005 Laurent A.V. Szyster

This library is free software; you can redistribute it and/or modify
it under the terms of version 2 of the GNU General Public License as
published by the Free Software Foundation.

	http://www.gnu.org/copyleft/gpl.html

This library is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

You should have received a copy of the GNU General Public License
along with this library; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

*/

/*
 * encode an array of strings as netunicode, ready to be encoded in 
 * UTF-8 or any other UNICODE encoding available to browsers ...
 * 
 */
function netunicode (array) {
	var buffer = "";
	var item;
	for (var i = 0; i < array.length; i++) {
		item = array[i];
		buffer += item.length.toString () + ":" + item + ",";
	};
	return buffer;
};

/* 
 * decode netunicode from the buffer and return a new Array or a 
 * string if there is no netstring at the start of the buffer.
 * 
 */
function netunidecode (buffer, strip) {
	var result = buffer;
	var size = buffer.length;
	var prev = 0;
	var pos, length, next, i;
	while (prev < size) {
		pos = buffer.indexOf (":", prev);
		if (pos < 1) {
			prev = size;
		} else {
			length = parseInt (buffer.substring (prev, pos))
			if (isNaN (length)) {
				prev = size;
			} else {
				next = pos + length + 1;
				if (next >= size) {
					prev = size;
				} else {
					if (buffer.charAt (next) == ",") {
						if (typeof result == "string") {
							result = new Array ();
							i = 0;
						} else {
							i = result.length;
						};
						if (strip == false | next-pos>1) {
							result[i] = buffer.substring (pos+1, next);
							};
						prev = next + 1;
					} else {
						prev = size;
					}
				}
			}
		}
	}
	return result;
};
	

/*
 * Make a tree of arrays and strings from nested netunicodes in a buffer
 * 
 */
function netunitree (buffer) {
	var netunicodes = netunidecode (buffer)
	if (typeof netunicodes == "string") {
		return buffer;
		
	} else {
		for (var i = 0; i < netunicodes.length; i++) {
			netunicodes[i] = netunitree (netunicodes[i])
		};
		return netunicodes;
		
	}
};

	
/*
 * 
 * TODO: outline a DOM tree from root, with the netunicode string of
 *       each element set as the named attribute, the practical way
 *       to produce something like:
 * 
 * <tag pns="5:Names,6Public,">
 * 	<tag>Names</tag>
 *  <tag>Public</tag>
 * </tag>
 * 
 */
function netoutline (buffer, root, attribute) {};
	
	
/* 
 * This is truly a validator that produce valid Public Names from what 
 * was found in the buffer.
 * 
 */
 
function publicnames (buffer, field, horizon) {
    var names = netunidecode (buffer, true);
    if (typeof names == "string") {
    	for (var i = 0; i < field.length; i++) {
    		if (names == field[i]) {
    			return "";
    			
    		}
    	}
        field[field.length] = names;
        return names;

    } else {
        var valid = new Array ();
        for (var i = 0; i < names.length; i++) {
            n = publicnames (names[i], field, horizon)
            if (n != "") {
                valid[valid.length] = n;
                if (field.length >= horizon) {
                    break;

                }  
            }
        };
        if (valid.length > 1) {
            valid.sort();
            return netunicode (valid);

        };
        if (valid.length > 0) {
            return valid[0];
            
        };
        return "";

	}
};

/*
 * Validate buffer as Public Names, using a cache of contexts first
 * 
 */

function publicnames_as (buffer, contexts) {
	try {
		return contexts[buffer];
		
	} catch (e) {
		var field = new Array ();
		if (buffer == publicnames (buffer, field)){
			contexts[buffer] = field;
			return field;
			
		} else {
			contexts[buffer] = null;
			return null;
			
		}
	}
};

function publicnames_in (buffer, contexts) {
	try {
		return contexts[buffer];
		
	} catch (e) {
		var field = new Array ();
		if (buffer == publicnames (buffer, field)){
			return field;
			
		} else {
			return null;
			
		}
	}
};
	
	
/* It's a 16bit wide world baby!
 * 
 * So Public Names are now based on netunicodes instead of netstrings. 
 * 
 * Without much loss of functionality, because Public Names must also be
 * encoded as UTF-8 in ... 8bit netstrings, allowing all those 7bit ASCII 
 * applications to still access PNS.
 * 
 */	