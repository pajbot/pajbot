function get_donations(client_id, access_token, on_finished, limit, offset, date_from)
{
    var donations = [];
    var streamtip_url = 'https://streamtip.com/api/tips';
    if (typeof date_from !== 'undefined') {
        streamtip_url = streamtip_url + '?date_from='+date_from;
    }
    $.ajax({
        url: streamtip_url,
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
    });
}

function get_donations_2(client_id, access_token, on_finished, limit, offset, date_from)
{
    var donations = [];
    var streamtip_url = 'https://streamtip.com/api/tips/leaderboard';
    if (typeof date_from !== 'undefined') {
        streamtip_url = streamtip_url + '?date_from='+date_from;
    }
    $.ajax({
        url: streamtip_url,
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
    });
}

function getSortedKeys(obj) {
    var keys = []; for(var key in obj) keys.push(key);
    return keys.sort(function(a,b){return obj[b]-obj[a]});
}

function streamtip_connect(client_id, access_token, on_error, on_new_tip, on_authenticated)
{
    var socket = io.connect('https://streamtip.com', {
            query: 'client_id='+encodeURIComponent(client_id)+'&access_token='+encodeURIComponent(access_token)
            });

    socket.on('authenticated', function() {
        console.log('authenticated');
        if (on_authenticated !== undefined) {
            on_authenticated();
        }
    });

    socket.on('error', on_error);
    socket.on('newTip', on_new_tip);
}
