/* Copyright (C) 2007 Laurent A.V. Szyster | Copyleft GPL 2.0 */

JSON.errors['401'] = function not_authorized (url, object) {
    HTML.classAdd($('inspect_object'), ['hidden']);
    HTML.classRemove($('login_password'), ['hidden']);
    $('pass').focus();
}
function login (element) {
    JSON.GET(
        '/root', 
        HTML.query(element), 
        function ok (text) {
            HTML.classAdd($('login_password'), ['hidden']);
            HTML.classRemove($('inspect_object'), ['hidden']);
            $('object').focus();
        });
}
function inspect (element) {
    JSON.POST('inspect', HTML.query(element), JSON.update());
}