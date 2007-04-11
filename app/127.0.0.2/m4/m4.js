/* Copyright (C) 2007 Laurent A.V. Szyster

 This library is free software; you can redistribute it and/or modify
 it under the terms of version 2 of the GNU General Public License as
 published by the Free Software Foundation.

    http://www.gnu.org/copyleft/gpl.html

 This library is distributed in the hope that it will be useful, but
 WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

 You should have received a copy of the GNU General Public License
 along with this library; if not, write to the Free Software
 Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA */

// Prototype's defacto standard convenience in a browser.
var $ = function (id) {return document.getElementById(id)};

var PNS = {
	statements: {}, // all statements articulated in this context
	indexes: {}, // an index of names validated in this context
	contexts: {}, // 
};
PNS.netunicode = function (s, sb) {
	sb.push(s.length); sb.push(":"); sb.push(s); sb.push(",");
}
/**
 * Encode an array of strings (or anything that [].join('') can join) into
 * netunicodes, return a string.
 */
PNS.netunicodes = function (list) {
	var s, sb = [];
	for (var i=0; i < list.length; i++) {
		s=list[i]; 
		sb.push(s.length); sb.push(":"); sb.push(s); sb.push(",");
	};
	return sb.join('');
};
/**
 * Push in a list the unidecoded strings found in the buffer, eventually
 * stripping empty strings (0:,) if strip is true, returns the extended
 * array or the one created if the list given was null and that at least
 * one netunicoded string was found at the buffer's start.
 */
PNS.netunidecodes = function (buffer, list, strip) {
	var size = buffer.length;
	var prev = 0;
	var pos, L, next;
	while (prev < size) {
		pos = buffer.indexOf(":", prev);
		if (pos < 1) prev = size; else {
			L = parseInt(buffer.substring(prev, pos))
			if (isNaN(L)) prev = size; else {
				next = pos + L + 1;
				if (next >= size) prev = size; else {
					if (buffer.charAt(next) != ",") prev = size; else {
						if (list==null) list = new Array();
						if (strip | next-pos>1)
							list.push(buffer.substring(pos+1, next));
						prev = next + 1;
					}
				}
			}
		}
	}
	return list;
};
/**
 * Push in sb an HTML representation of the nested netunicodes found in
 * the buffer, as nested span elements with articulated Public Names set
 * as title attribute and inarticulated unidecoded strings as CDATA.
 */
PNS.netHTML = function (buffer, sb) {
	var articulated = PNS.netunidecodes (buffer, new Array(), false);
	if (articulated.length == 0) {sb.push('<span>'); sb.push(buffer);}
	else {
		sb.push('<span title="'); sb.push(buffer); sb.push('">');
		for (var i=0, L=articulated.length; i < L; i++)
			PNS.netHTML(articulated[i], sb);
	}
	sb.push('</span>');
	return sb
}
/**
 * Articulate a JavaScript value as valid Public Names. 
 */
PNS.names_public = function (item, field) {
	if (typeof item == 'object') {
		var list = new Array(), L=item.length, n;
		if (L == null) for (var k in item) {
			n = PNS.names_public([k, item[k]], field);
			if (n!=null) list.push(n);
		} else for (var i=0; i < L; i++) {
			n = PNS.names_public(item[i], field);
			if (n!=null) list.push(n);
		}
		L = list.length;
		if (L > 1) {list.sort(); return PNS.netunicodes(list);}
		else if (L == 1) return list[0];
		else return null;
	} else item = item.toString(); 
	if (field[item] == null) {field[item] = true; return item;}
	else return null;
} // this is for articulation of JSON only ...
/**
 * Returns null or a valid Public Names if one could be articulated from
 * the given string buffer and semantic field.
 */
PNS.names_validate = function (buffer, field) {
    var names = PNS.netunidecodes(buffer, null, true);
    if (names == null) {
        if (field[buffer] != null) return null;
        field[buffer] = true; return buffer;
    } else {
        var valid = new Array ();
        for (var i=0, L=names.length; i < L; i++) {
            n = PNS.names_validate(names[i], field);
            if (n != null) valid.push(n);
        };
        if (valid.length > 1) {valid.sort(); return PNS.netunicodes(valid);};
        if (valid.length > 0) return valid[0];
        return null;
	}
} // this is it for validation & articulation ;-)
PNS.languages = {
	'ASCII':[
	    /\s*[?!.](?:\s+|$)/, // point, split sentences
	    /\s*[:;](?:\s+|$)/, // split head from sequence
	    /\s*,(?:\s+|$)/, // split the sentence articulations
	    /(?:(?:^|\s+)[({\[]+\s*)|(?:\s*[})\]]+(?:$|\s+))/, // parentheses
	    /\s+[-]+\s+/, // disgression
	    /["]/, // citation
	    /(?:^|\s+)(?:(?:([A-Z]+[\S]*)(?:$|\s)?)+)/, // private names
	    /\s+/, // white spaces
	    /['\\\/*+\-#]/ // common hyphens
		]
	};
PNS.SAT_articulators = function (articulators) {
    return new RegExp(
        '(?:^|\\s+)((?:' + articulators.join (')|(?:') + '))(?:$|\\s+)'
        );
}
PNS.SAT = function (text, articulators, depth, chunks, chunk) {
    var i, L, articulated, name, field;
	var bottom = articulators.length;
    while (true) {
        var texts = text.split(articulators[depth]); depth++;
        if (texts.length > 1) {
		    articulated = new Array();
	        for (i=0, L=texts.length; i<L; i++) if (texts[i].length > 0)
	        	articulated.push(texts[i]);
	        L=articulated.length;
	        if (L > 1) break; else if (L == 1) text = articulated[0];
        } else if (texts.length == 1 && texts[0].length > 0) text = texts[0];
        if (depth == bottom) return text;
    }
    if (depth < bottom) 
    	if (chunk == null) {
		    var names = new Array(); for (i=0; i<L; i++) names.push(
	    		PNS.SAT(articulated[i], articulators, depth)
	    		);
		    return names;
	    } else {
	        for (i=0; i<L; i++) {
	            text = articulated[i];
	            if (text.length > chunk)
	                PNS.SAT(text, articulators, depth, chunks, chunk);
		    	else {
		    		field = new Object();
			    	name = PNS.names_public (
			    		PNS.SAT(text, articulators, depth), field
			    		);
			    	if (name!=null) chunks.push([name, text, field]);
		    	} 
	    	} return null;
	    }
    else return articulated;
}
PNS.context = function (buffer) {
	var cached = PNS.contexts[buffer];
	if (cached == null) {
		var field = new Object();
		if (buffer == PNS.names_validate (buffer, field)) {
			PNS.contexts[buffer] = field;
			return field;
		} else 
			return null;
	}
	return cached; 
}
PNS.subject = function (buffer) {
	if (this.indexes[buffer] != null) return;
	var names = PNS.unidecodes(buffer, null);
	if (names == null)
		PNS.indexes[buffer] = true;
	else {
		var pn, indexed; 
		for (var i=0; i<names.length; i++) {
			pn = names[i]; indexed = this.indexes[pn];
			if (indexed == null)
				PNS.indexes[pn] = buffer;
			else
				PNS.indexes[pn] = publicNames(
					indexed + buffer, new Object()
					);
			PNS.index(pn);
		}
	}
}
PNS.statement = function(subject, predicate, object, context) {
	this.context(context); 
	this.subject(subject);
	objects = PNS.statements[subject + predicate];
	if (objects == null) 
		PNS.statements[subject + predicate] = {context: object}; 
	else objects[context] = object || '';
}

var URL = {};
URL.formencode = function (sb, query) {
    start = sb.length;
    for (key in query) {
        sb.push ('&'); 
        sb.push (key); // TODO: URL quote ?
        sb.push ('='); 
        sb.push (query[key]); // TODO: URL quote ?
    }
    if (sb.length - start > 1) sb[start] = '?';
    return sb;
}

var JSON = {};
JSON.escaped = {
    '\b': '\\b',
    '\t': '\\t',
    '\n': '\\n',
    '\f': '\\f',
    '\r': '\\r',
    '"' : '\\"',
    '\\': '\\\\'
    };
JSON.escape = function (a, b) {
    var c = JSON.escaped[b];
    if (c) return c;
    c = b.charCodeAt();
    return '\\u00'+Math.floor(c/16).toString(16)+(c%16).toString(16);
    }
JSON.decode = function (s) {
    try {
        if (/^("(\\.|[^"\\\n\r])*?"|[,:{}\[\]0-9.\-+Eaeflnr-u \n\r\t])+?$/.
                test(s))
            return eval('(' + s + ')');
    } catch (e) {
	    throw new SyntaxError("parseJSON");
	}
}
JSON.encode = function (sb, v) {
    switch (typeof v) {
    case 'string':
    	sb.push ('"');
        if (/["\\\x00-\x1f]/.test(v)) 
        	sb.push(v.replace(/([\x00-\x1f\\"])/g, JSON.escape));
        else
        	sb.push(v);
    	sb.push ('"');
		return sb;
    case 'number':
    	sb.push (isFinite(v) ? v : "null"); return sb;
    case 'boolean':
    	sb.push (v); return sb;
    case 'undefined':
    case 'function':
    case 'unknown':
        return sb;
    case 'object': {
		if (v == null) sb.push ("null");
        else if (v.length == null) { // Object
        	var fun = JSON.encode;
        	sb.push ('{');
        	for (k in v) {
        		fun(sb, k), sb.push (':'); fun (sb, v[k]); sb.push (',');
        		}
        	var last = sb.length-1;
        	if (sb[last] == ',') sb[last] = '}';
        	else sb[last] = '{}'
        } else { // Array
        	var fun = JSON.encode;
        	sb.push ('[');
        	for (var i=0, L=v.length; i<L; i++) {
        		fun (sb, v[i]); sb.push (',')
        		}
        	var last = sb.length-1;
        	if (sb[last] == ',') sb[last] = ']';
        	else sb[last] = '[]'
        }
	    return sb;
    } default:
        v = v.toString();
    	sb.push ('"');
        if (/["\\\x00-\x1f]/.test(v)) 
        	sb.push(v.replace(/([\x00-\x1f\\"])/g, JSON.escape));
        else
        	sb.push(v);
    	sb.push ('"');
	    return sb;
    }
}
JSON.innerHTML = function (sb, v) {
    switch (typeof v) {
    case 'string':
    	sb.push ('<span class="JSONstring">');
        if (/["\\\x00-\x1f]/.test(v)) 
        	sb.push(v.replace(/([\x00-\x1f\\"])/g, JSON.escape));
        else
        	sb.push(v);
    	sb.push ('</span>');
		return sb;
    case 'number':
    	sb.push ('<span class="JSONnumber">');
    	sb.push (isFinite(v) ? v : "null");
    	sb.push ('</span>');
    	return sb;
    case 'boolean':
    	sb.push ('<span class="JSONboolean">');
    	sb.push (v); 
    	sb.push ('</span>');
    	return sb;
    case 'undefined':
    case 'function':
    case 'unknown':
        return sb;
    case 'object': {
		if (v == null) sb.push ('<span class="JSONnull">null</span>'); 
        else if (v.length == null) { // Object
        	sb.push ('<table class="JSONobject"><tbody>');
        	var fun = JSON.encode;
        	for (k in v) {
        		sb.push ('<tr><td class="JSONname">');
        		fun(sb, k), 
        		sb.push ('</td><td class="JSONvalue">');
        		fun (sb, v[k]); 
        		sb.push ('</td></tr>');
        		}
        	sb.push ('</tbody></table>');
        } else { // Array
        	sb.push ('<div class="JSONarray">');
        	var fun = JSON.encode;
        	for (var i=0, L=v.length; i<L; i++) fun (sb, v[i])
        	sb.push ('</div>');
        }
        return sb;
    } default:
    	sb.push ('<span class="');
    	sb.push (typeof v);
    	sb.push ('">');
        v = v.toString();
        if (/["\\\x00-\x1f]/.test(v)) 
        	sb.push(v.replace(/([\x00-\x1f\\"])/g, JSON.escape));
        else
        	sb.push(v);
    	sb.push ('</span>');
		return sb;
    }
}
JSON.regular = function (pattern, object) {
	// -> innerHTML	
}

var HTTP = {
    requests: {},
    timeout: 3000 // 3 seconds
    };
HTTP.request = function (headers) {
    var req;
    if (window.XMLHttpRequest) // Mozilla, Safari, ...
        req = new XMLHttpRequest();
        if (req.overrideMimeType && (
            navigator.userAgent.match(/Gecko\/(\d{4})/) || [0,2005]
            )[1] < 2005)
            headers['Connection'] = 'close';
    else if (window.ActiveXObject) {
        try { // IE
            req = new ActiveXObject("Msxml2.XMLHTTP");
        } catch (e) {
            try {req = new ActiveXObject("Microsoft.XMLHTTP");} 
            catch (e) {;}
        }
    }
    return req;
}
HTTP.collect = function (key) {
    try {HTTP.requests[key].abort()} catch (e) {}
    delete HTTP.requests[key];
}
HTTP.GET = function (url, headers, timeout) {
    var key = ['GET', url].join (' ');
    var req = HTTP.request(headers);
    if (!req) return null;
    HTTP.requests[key] = req;
    setTimeout (['HTTP.collect("', key, '")'].join (''), timeout);
    req.open('GET', url, true);
    if (headers) for (var name in headers) 
        req.setRequestHeader(name, headers[name]);
    req.send(null);
    return req;
}
HTTP.POST = function (url, headers, body, timeout) {
    var key = ['POST', url].join (' ');
    var req = HTTP.request(headers);
    if (!req) return null;
    HTTP.requests[key] = req;
    setTimeout (['HTTP.collect("', key, '")'].join (''), timeout);
    req.open('POST', url, true);
    if (headers) for (var name in headers) 
        req.setRequestHeader(name, headers[name]);
    req.send(body);
    return req;
}
HTTP.JSON_continue = function (req, ok, error, exception) {
    return function () {
        try {
            if (req.readyState == 4) {
                try {
                    if (req.status == 200) 
                        ok (JSON.decode(req.responseText));
                    else if (error)    error (req.status)
                } catch (e) {error (0)}
            }
        } catch (e) {if (exception) exception(e);}
    }
}
HTTP.GET_json = function (url, query, ok, error, exception) {
    req = HTTP.GET (URL.formencode ([url], query).join (''), {
        'Accept': 'application/json'
        }, HTTP.timeout);
    if (req == null) {if (exception) exception ();}
    else req.onreadystatechange = HTTP.JSON_continue (
        req, ok, error, exception
        );
}
HTTP.POST_json = function (url, object, ok, error, exception) {
    req = HTTP.POST (url, {
        'Content-Type': 'application/json; charset=UTF-8', 
        'Accept': 'application/json'
        }, JSON.encode ([], object).join (''), HTTP.timeout);
    if (req == null) {if (exception) exception ();}
    else req.onreadystatechange = HTTP.JSON_continue (
        req, ok, error, exception
        )
}

