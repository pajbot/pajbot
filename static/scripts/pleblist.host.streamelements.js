var streamelements_socket;

function streamelements_get_donations(access_token, on_finished, limit, offset, date_from)
{
    var donations = [];
    var api_url = 'https://api.streamelements.com/kappa/v1/tips';
    if (typeof date_from !== 'undefined') {
        api_url = api_url + '?date_from='+date_from;
    }
    request_arguments = {
        'limit': limit,
        'offset': offset,
    };
    $.ajax({
        url: api_url,
        timeout: 1500,
        cache: false,
        data: request_arguments,
        beforeSend: function(xhr) {
            xhr.setRequestHeader('Authorization', 'OAuth ' + access_token);
        },
        success: function(data) {
            var donations = [];

            for (var i=0; i<data.total; ++i) {
                donations.push(data.docs[i].donation);
            }

            on_finished(donations);

            console.log(data);
        },
    });
}

function streamelements_add_tip(tip)
{
    if (tip.user.avatar === undefined) {
        tip.user.avatar = 'https://cdn.pajlada.se/images/profile-placeholder.png';
    }

    console.log(tip);
    console.log(tip.currency);
    console.log('xd');

    var currencySymbol = '$';

    if (currency_symbols[tip.currency] !== undefined) {
        currencySymbol = currency_symbols[tip.currency];
    }

    add_tip(tip.user.username, tip.user.avatar, tip.amount, null, tip.message, currencySymbol);
}

function streamelements_add_tip_ws(tip)
{
    var avatar = 'https://cdn.pajlada.se/images/profile-placeholder.png';
    var currencySymbol = '$';

    if (currency_symbols[tip.currency] !== undefined) {
        currencySymbol = currency_symbols[tip.currency];
    }

    add_tip(tip.name, avatar, tip.amount, null, tip.message, currencySymbol);
}


function streamelements_connect(access_token)
{
    streamelements_get_donations(access_token, function(donations, raw_json) {
        donations.reverse();
        for (tip_id in donations) {
            streamelements_add_tip(donations[tip_id]);
        }
    }, 10, 0);

    var socket = io.connect('https://api.streamelements.com', {
        path: '/socket'
    });

    streamelements_socket = socket;

    socket.on('error', function(err) {
        var code = err.split('::')[0];

        if (code === '401') {
            console.log('Authentication failed');
        } else if (code == '429') {
            console.log('rate limited');
        } else if (code == '400') {
            console.log('bad request');
        }
    });

    socket.on('connect', function() {
        socket.emit('authenticate:oauth', { token: access_token });
    });

    socket.on('authenticated', function() {
        console.log('we are now authenticated');
    });

    socket.on('newTip', function(data) {
    });

    socket.on('event', events);
    socket.on('event:test', events);

    function events(payload) {
        var data = payload;
        if (payload.test !== undefined) {
            data = payload.event;
        }

        if (data.type == 'tip') {
            if (data.avatar === undefined) {
                data.avatar = 'https://cdn.pajlada.se/images/profile-placeholder.png';
            }
            streamelements_add_tip_ws(data);
        }
        console.log(data);
        console.log('new event of type ', data.type);
    }
}
