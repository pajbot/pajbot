function streamtip_get_donations(client_id, access_token, on_finished, limit, offset, date_from)
{
    var donations = [];
    var api_url = 'https://streamtip.com/api/tips';
    if (typeof date_from !== 'undefined') {
        api_url = api_url + '?date_from='+date_from;
    }
    $.ajax({
        url: api_url,
        timeout: 1500,
        cache: false,
        dataType: 'jsonp',
        data: {
            'client_id': client_id,
            'access_token': access_token,
            'limit': limit,
            'offset': offset,
        },
    })
    .done(function(json) {
        var donations = [];

        if (json['tips'].length >= 1) {
            for (var i=0; i<json['tips'].length; ++i) {
                donations.push(json['tips'][i]);
            }
        }

        on_finished(donations, json);
    })
    .fail(function(xhrObj, textStatus) {
        console.log('Fail!' + textStatus);

        console.log('Retrying in 5 seconds...');
        setTimeout(function() {
            console.log('Retrying!');
            streamtip_get_donations(client_id, access_token, on_finished, limit, offset, date_from);
        }, 5000);
    });
}

function streamtip_add_tip(tip)
{
    add_tip(tip.username, tip.user.avatar, null, tip.cents, tip.note, tip.currencySymbol);
}

function streamtip_connect(access_token)
{
    streamtip_get_donations(streamtip_client_id, access_token, function(donations, raw_json) {
        donations.reverse();
        for (tip_id in donations) {
            var tip = donations[tip_id];
            if (tip.user === undefined) {
                // for manually added tips
                continue;
            }
            streamtip_add_tip(tip);
        }
    }, 10, 0);

    var socket = io.connect('wss://streamtip.com', {
        query: 'access_token='+encodeURIComponent(access_token)
    });

    socket.on('error', function(err) {
        console.log(err);
        var code = err.split('::')[0];

        if (code === '401') {
            console.log('Authentication failed');
        } else if (code == '429') {
            console.log('rate limited');
        } else if (code == '400') {
            console.log('bad request');
        }
    });

    socket.on('newTip', function(tip) {
        streamtip_add_tip(tip);
    });
}
