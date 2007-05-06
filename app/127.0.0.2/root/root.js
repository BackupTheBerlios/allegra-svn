JSON.errors['401'] = function not_authorized (url, object) {
    HTML.classAdd($('inspect_object'), ['hidden']);
    HTML.classRemove($('login_password'), ['hidden']);
    $('pass').focus();
}
function login () {
    JSON.GET(
        '/root', 
        HTML.query($('login_password')), 
        function ok (text) {
            HTML.classAdd($('login_password'), ['hidden']);
            HTML.classRemove($('inspect_object'), ['hidden']);
            $('object').focus();
        });
}
function inspect () {
    JSON.POST(
        'inspect', 
        HTML.query($('inspect_object')), 
        JSON.update('inspected')
        );
}