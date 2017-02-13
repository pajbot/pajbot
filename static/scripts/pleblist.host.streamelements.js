var streamelements_socket;

function streamelements_replay_activity(access_token, activity_id)
{
    $.ajax({
        url: 'https://api.streamelements.com/kappa/v1/activities/' + activity_id + '/replay',
        method: 'post',
        dataType: 'json',
        contentType: 'application/json',
        data: '{"_id":"' + activity_id + '","_username":"pajlada","type":"tip","data":{"username":"styler","amount":100,"currency":"DKK","message":"Keepo XDDDDD 4Head"},"createdAt":"2017-01-25T19:07:13.237Z"}',
        beforeSend: function(xhr) {
            xhr.setRequestHeader('Authorization', 'OAuth ' + access_token);
        },
        success: function(data) {
            console.log('successfully replayed');
            console.log(data);
        },
    });

}

function streamelements_get_donations(access_token, on_finished, limit, offset, date_from)
{
    var donations = [];
    var api_url = 'https://api.streamelements.com/kappa/v1/tips';
    if (typeof date_from !== 'undefined') {
        api_url = api_url + '?date_from='+date_from;
    }
    var request_arguments = {
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
        },
    });
}

function streamelements_add_tip(tip)
{
    if (tip.user.avatar === undefined) {
        tip.user.avatar = 'https://cdn.pajlada.se/images/profile-placeholder.png';
    }

    console.log(tip);

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
        console.error('[StreamElements] Error connecting to websocket', err);
    });

    socket.on('connect', function() {
        console.log('[StreamElements] Connected via WebSocket, authenticating...');
        socket.emit('authenticate:oauth', { token: access_token });
    });

    socket.on('authenticated', function() {
        console.log('[StreamElements] Authenticated via WebSocket');

        streamelements_replay_activity(access_token, '58a0b82f5c8663231e1f0b26');
    });

    socket.on('event', events);
    socket.on('tip', function(xD) {
        console.log(xD);
    });
    socket.on('tip-latest', function(xD) {
        console.log(xD);
    });
    socket.on('event:test', events);
    socket.on('event:update', function(xD) {
        console.log(xD);
    });

    function events(payload) {
        console.log('aaaaaa');
        console.log(payload);
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
