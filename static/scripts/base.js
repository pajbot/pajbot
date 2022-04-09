$.fn.api.settings.api = {
    get_user: '/api/v1/users/{username}',
    get_user_from_user_input: '/api/v1/users/{username}?user_input=true',
    edit_command: '/api/v1/commands/update/{id}',
    remove_command: '/api/v1/commands/remove/{id}',
    check_alias: '/api/v1/commands/checkalias',
    toggle_timer: '/api/v1/timers/toggle/{id}',
    remove_timer: '/api/v1/timers/remove/{id}',
    toggle_banphrase: '/api/v1/banphrases/toggle/{id}',
    remove_banphrase: '/api/v1/banphrases/remove/{id}',
    toggle_module: '/api/v1/modules/toggle/{id}',
    social_set: '/api/v1/social/{key}/set',
    clr_donation_save: '/api/v1/clr/donations/{widget_id}/save',
    commands: '/api/v1/commands/{raw_command_id}',
    get_twitter_follows: '/api/v1/twitter/follows',
    twitter_unfollow: '/api/v1/twitter/unfollow',
    twitter_follow: '/api/v1/twitter/follow',
};

$(document).ready(function() {
    $('#usersearch').form({
        fields: {
            username: 'empty',
        },
        onSuccess: function(settings) {
            document.location.href =
                '/user/' +
                encodeURIComponent($('#usersearch input.username').val());
            return false;
        },
    });
});

// parseUri 1.2.2
// (c) Steven Levithan <stevenlevithan.com>
// MIT License

function parseUri(str) {
    var o = parseUri.options,
        m = o.parser[o.strictMode ? 'strict' : 'loose'].exec(str),
        uri = {},
        i = 14;

    while (i--) uri[o.key[i]] = m[i] || '';

    uri[o.q.name] = {};
    uri[o.key[12]].replace(o.q.parser, function($0, $1, $2) {
        if ($1) uri[o.q.name][$1] = $2;
    });

    return uri;
}

parseUri.options = {
    strictMode: false,
    key: [
        'source',
        'protocol',
        'authority',
        'userInfo',
        'user',
        'password',
        'host',
        'port',
        'relative',
        'path',
        'directory',
        'file',
        'query',
        'anchor',
    ],
    q: {
        name: 'queryKey',
        parser: /(?:^|&)([^&=]*)=?([^&]*)/g,
    },
    parser: {
        strict: /^(?:([^:\/?#]+):)?(?:\/\/((?:(([^:@]*)(?::([^:@]*))?)?@)?([^:\/?#]*)(?::(\d*))?))?((((?:[^?#\/]*\/)*)([^?#]*))(?:\?([^#]*))?(?:#(.*))?)/,
        loose: /^(?:(?![^:@]+:[^:@\/]*@)([^:\/?#.]+):)?(?:\/\/)?((?:(([^:@]*)(?::([^:@]*))?)?@)?([^:\/?#]*)(?::(\d*))?)(((\/(?:[^?#](?![^?#\/]*\.[^?#\/.]+(?:[?#]|$)))*\/?)?([^?#\/]*))(?:\?([^#]*))?(?:#(.*))?)/,
    },
};
