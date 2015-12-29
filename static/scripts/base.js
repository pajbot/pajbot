$.fn.api.settings.api = {
    'get_user': '/api/v1/user/{username}',
    'pleblist_add_song': '/api/v1/pleblist/add',
    'pleblist_validate': '/api/v1/pleblist/validate',
    'pleblist_next_song': '/api/v1/pleblist/next',
    'get_pleblist_songs': '/api/v1/pleblist/list',
    'get_pleblist_songs_after': '/api/v1/pleblist/list/after/{id}',
    'edit_command': '/api/v1/command/update/{id}',
    'remove_command': '/api/v1/command/remove/{id}',
    'check_alias': '/api/v1/command/checkalias',
    'toggle_timer': '/api/v1/timer/toggle/{id}',
    'remove_timer': '/api/v1/timer/remove/{id}',
    'toggle_banphrase': '/api/v1/banphrase/toggle/{id}',
    'remove_banphrase': '/api/v1/banphrase/remove/{id}',
    'toggle_module': '/api/v1/module/toggle/{id}',
};

$(document).ready(function() {
    $('#usersearch').form({
        onSuccess: function(settings) {
            document.location.href = '/user/'+$('#usersearch input.username').val();
            return false;
        }
    });
});

// parseUri 1.2.2
// (c) Steven Levithan <stevenlevithan.com>
// MIT License

function parseUri (str) {
    var o   = parseUri.options,
        m   = o.parser[o.strictMode ? "strict" : "loose"].exec(str),
        uri = {},
        i   = 14;

    while (i--) uri[o.key[i]] = m[i] || "";

    uri[o.q.name] = {};
    uri[o.key[12]].replace(o.q.parser, function ($0, $1, $2) {
        if ($1) uri[o.q.name][$1] = $2;
    });

    return uri;
};

parseUri.options = {
    strictMode: false,
    key: ["source","protocol","authority","userInfo","user","password","host","port","relative","path","directory","file","query","anchor"],
    q:   {
        name:   "queryKey",
        parser: /(?:^|&)([^&=]*)=?([^&]*)/g
    },
    parser: {
        strict: /^(?:([^:\/?#]+):)?(?:\/\/((?:(([^:@]*)(?::([^:@]*))?)?@)?([^:\/?#]*)(?::(\d*))?))?((((?:[^?#\/]*\/)*)([^?#]*))(?:\?([^#]*))?(?:#(.*))?)/,
        loose:  /^(?:(?![^:@]+:[^:@\/]*@)([^:\/?#.]+):)?(?:\/\/)?((?:(([^:@]*)(?::([^:@]*))?)?@)?([^:\/?#]*)(?::(\d*))?)(((\/(?:[^?#](?![^?#\/]*\.[^?#\/.]+(?:[?#]|$)))*\/?)?([^?#\/]*))(?:\?([^#]*))?(?:#(.*))?)/
    }
};
