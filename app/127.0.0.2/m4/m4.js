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

// Class prototyping in JavaScript (not in C++, Ruby or Python ,-)
function Prototype (protocols) {
	Fun = function () {this.initialize.apply(this, arguments)};
	for (var proto, i=0, L=protocols.length; i<L; i++) {
		proto = protocols[i];
		for (property in proto) 
			Fun.prototype[property] = proto[property];
	}
	return Fun;
} // this is all the OO you need to have instances of mix-in classes.

var PNS = {
    statements: {}, // all statements articulated in this context
    indexes: {}, // an index of names validated in this context
    routes: {}, // 
    HORIZON: 126 // lower to limit CPU usage ?
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
                        if (list==null) list = [];
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
    var articulated = this.netunidecodes (buffer, [], false);
    if (articulated.length == 0) {sb.push('<span>'); sb.push(buffer);}
    else {
        sb.push('<span pns="'); 
        sb.push (buffer); // TODO: escape ?
        sb.push('">');
        for (var i=0, L=articulated.length; i < L; i++)
            this.netHTML(articulated[i], sb);
    }
    sb.push('</span>');
    return sb
}
PNS.encode = function (item, field) {
    if (typeof item == 'object') {
        var list = [], L=item.length, n;
        if (L == null) for (var k in item) {
            n = this.encode([k, item[k]], field);
            if (n!=null) list.push(n);
        } else for (var i=0; i < L; i++) {
            n = this.encode(item[i], field);
            if (n!=null) list.push(n);
        }
        L = list.length;
        if (L > 1) {list.sort(); return this.netunicodes(list);}
        else if (L == 1) return list[0];
        else return null;
    } else item = item.toString(); 
    if (field[item] == null) {field[item] = true; return item;}
    else return null;
}
PNS.public_names = function (names, field) {
    var n, s, valid = [];
    for (var i=0, L=names.length; i < L; i++) {
        buffer = names[i];
        if (field[buffer] != null) continue;
        n = this.netunidecodes (buffer, null, true)
        if (n == null) {
            valid.push(buffer); 
            field[buffer] = true; 
            field[''] += 1;
        } else {
            s = this.public_names (n, field);
            if (s != null) {
                valid.push(s); 
                field[s] = true; 
                field[''] += 1;
            }
        }
    };
    if (valid.length > 1) {valid.sort(); return this.netunicodes(valid);};
    if (valid.length > 0) return valid[0];
    return null;
}
PNS.index = function (subject, context) {
    if (this.indexes[subject] == null) {
        var field = {'':0};
        if (subject == this.public_names(
        	PNS.netunidecodes (subject), field
        	)) {
            var index, names; 
            for (var pn in field) if (pn != '') {
                index = this.indexes[pn];
                if (index == null)
                    this.indexes[pn] = subject;
                else if (index != false){
                   names = this.netunidecodes(index, []);
                   names.push (subject);
                   index = {'':0};
                   this.indexes[pn] = this.public_names(names, field);
                   if (field[''] > this.HORIZON)
                       this.indexes[pn] = false;
                }
                routes = this.routes[pn];
                if (routes == null)
                    this.routes[pn] = [context];
                else
                    if (routes.indexOf (context) == -1)
                        routes.push (context);
            }
        }
    } 
    if (context != null) {
        var routes = this.routes[subject];
        if (routes == null)
            this.routes[subject] = [context];
        else
            if (routes.indexOf (context) == -1)
                routes.push (context);
        this.graph (context);
    }
}
PNS.search = function(names) {
    
}
PNS.statement = function (subject, predicate, object, context) {
    this.index (subject, context);
    var subject_predicate = this.netunicodes([subject, predicate]);
    var objects = this.statements[subject_predicate];
    if (objects == null) 
        this.statements[subject_predicate] = {context: object}; 
    else 
        objects[context] = (!object) ? "": object; // for questions too ;-)
}
PNS.languages = {
    'SAT':[
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
PNS.articulator = function (words) {
    return new RegExp(
        '(?:^|\\s+)((?:' + words.join (')|(?:') + '))(?:$|\\s+)'
        );
}
PNS.sat = function (text, articulators, depth, chunks, chunk) {
    var i, L, texts, articulated, subject;
    var bottom = articulators.length;
    while (true) {
        texts = text.split(articulators[depth]); 
        depth++;
        if (texts.length > 1) {
            articulated = [];
            for (i=0, L=texts.length; i<L; i++) 
                if (texts[i].length > 0)
                    articulated.push(texts[i]);
            L=articulated.length;
            if (L > 1) 
                break; 
            else 
                if (L == 1) 
                    text = articulated[0];
        } else 
            if (texts.length == 1 && texts[0].length > 0) 
                text = texts[0];
        if (depth == bottom) 
            return [text];
    }
    if (depth < bottom) 
        if (chunk == null) {
            var sat, names = [], field = {'':0}; 
            for (i=0; i<L; i++) {
                sat = this.public_names (
                    this.sat (articulated[i], articulators, depth), field
                    );
                if (sat != null) names.push (sat);
            }
            return names;
        } else {
            var sat, field = {'':0};
            for (i=0; i<L; i++) {
                text = articulated[i];
                if (text.length > chunk)
                    this.sat(text, articulators, depth, chunks, chunk);
                else {
                    sat = this.public_names (
                        this.sat (text, articulators, depth), field
                        );
                    if (sat!=null) chunks.push([sat, text]);
                } 
            } return chunks;
        }
    else return articulated;
}
PNS.articulate_chunk = function (text, lang, context, chunk) {
    if (lang == null || this.languages[lang] == null) return;
    var chunks = this.sat (text, lang, 0, [], chunk);
    for (var i=0, L=chunks.length; i<L; i++) {
        this.statement(chunks[i][0], lang, chunks[i][1], context)
    }
}
PNS.articulate_xml = function (element, lang, context, chunk) {
    // override with xml:lang of the element
    if (lang == null || this.languages[lang] == null) 
        throw "PNS error: undefined language.";
    // articulate child text and element nodes in the same chunks list ;-)
    var chunks = [];
    this.articulate_chunk (text, lang, 0, chunks, chunk);
    for (var i=0, L=chunks.length; i<L; i++) {
        this.statement(chunks[i][0], lang, chunks[i][1], context)
    }
}
PNS.articulate = function (text_or_element, lang, context) {
    if (lang == null || this.languages[lang] == null)
        throw "this.error: undefined language.";
    this.statement (this.public_names (
        this.sat (text, this.languages[lang], 0), {'':0}
        ), lang, text, context);
}

var JSON = {};
JSON.decode = function (s) {
    try {
        if (/^("(\\.|[^"\\\n\r])*?"|[,:{}\[\]0-9.\-+Eaeflnr-u \n\r\t])+?$/.
                test(s))
            return eval('(' + s + ')');
    } catch (e) {
        throw new SyntaxError("parseJSON");
    }
}
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
    var c = this.escaped[b];
    if (c) return c;
    c = b.charCodeAt();
    return '\\u00'+Math.floor(c/16).toString(16)+(c%16).toString(16);
    }
JSON.encode = function (v, sb) {
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
            sb.push ('{');
            for (k in v) {
                this.encode (k, sb), sb.push (':'); 
                this.encode (v[k], sb); sb.push (',');
                }
            var last = sb.length-1;
            if (sb[last] == ',') sb[last] = '}';
            else sb[last] = '{}'
        } else { // Array
            sb.push ('[');
            for (var i=0, L=v.length; i<L; i++) {
                this.encode (v[i], sb); sb.push (',')
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
JSON.innerHTML = function (v, sb) {
    switch (typeof v) {
    case 'string':
        sb.push ('<span class="JSONstring">');
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
            for (k in v) {
                sb.push ('<tr><td class="JSONname">');
                this.innerHTML (k, sb), 
                sb.push ('</td><td class="JSONvalue">');
                this.innerHTML (v[k], sb); 
                sb.push ('</td></tr>');
                }
            sb.push ('</tbody></table>');
        } else { // Array
            sb.push ('<div class="JSONarray">');
            for (var i=0, L=v.length; i<L; i++) this.innerHTML (v[i], sb)
            sb.push ('</div>');
        }
        return sb;
    } default:
        sb.push ('<span class="');
        sb.push (typeof v);
        sb.push ('">');
        sb.push(v.toString());
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
HTTP.formencode = function (sb, query) {
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
    var req = this.request(headers);
    if (!req) return null;
    this.requests[key] = req;
    setTimeout (['HTTP.collect("', key, '")'].join (''), timeout);
    req.open('GET', url, true);
    if (headers) for (var name in headers) 
        req.setRequestHeader(name, headers[name]);
    req.send(null);
    return req;
}
HTTP.POST = function (url, headers, body, timeout) {
    var key = ['POST', url].join (' ');
    var req = this.request(headers);
    if (!req) return null;
    this.requests[key] = req;
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
    req = this.GET (this.formencode ([url], query).join (''), {
        'Accept': 'application/json'
        }, this.timeout);
    if (req == null) {if (exception) exception ();}
    else req.onreadystatechange = this.JSON_continue (
        req, ok, error, exception
        );
}
HTTP.POST_json = function (url, object, ok, error, exception) {
    req = this.POST (url, {
        'Content-Type': 'application/json; charset=UTF-8', 
        'Accept': 'application/json'
        }, JSON.encode (object, []).join (''), this.timeout);
    if (req == null) {if (exception) exception ();}
    else req.onreadystatechange = this.JSON_continue (
        req, ok, error, exception
        );
} // why bother with periodicals in a one minute web page?

var HTML = {}; // more conveniences for more applications for more ... 
HTML.POST_json = function (el, ok, error, exception) {
	var query = {}, children = el.parentNode.childNodes, child;
	for (var i=0, L=children.length; i<L; i++) {
		child = children[i];
		if (
			child.nodeName.toLowerCase() == 'input' && 
			child.name != null &&
		 	/(text)|(password)|(checkbox)|(radio)|(hidden)/.test(
		 		(child.type||'').toLowerCase()
		 		)
		)
		query[child.name] = child.value;
	}
	HTTP.POST_json(el.value||'', query, ok, error, exception);
}
HTML.JSON_update = function (id) {
	return function (json) {
		document.getElementById(id).innerHTML = JSON.innerHTML(
			json, []
			).join ('');
	}
} // ... here just enough to bootstrap a web user interface from JSON.

