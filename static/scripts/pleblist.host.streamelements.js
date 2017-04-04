var streamelements_socket;

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

            for (var i=0; i<data.docs.length; ++i) {
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
    }, 50, 0);

    var socket = io.connect('https://realtime.streamelements.com', {
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
    });

    socket.on('tip-latest', tipHandler);
    socket.on('event:test', testEventHandler);
    socket.on('event:update', realEventHandler);

    function testEventHandler(payload) {
        if (payload.listener === 'tip-latest') {
            tipHandler(payload.event);
        }
    }

    function realEventHandler(payload) {
        if (payload.name === 'tip-latest') {
            tipHandler(payload.data);
        }
    }

    function tipHandler(payload) {
        console.log('[StreamElements] Got new tip:', payload);
        streamelements_add_tip_ws(payload);
    }
}
