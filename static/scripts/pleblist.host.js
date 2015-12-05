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

function add_tip(username, avatar, cents, note)
{
    cents = String(cents);
    var amount = '$' + cents.substring(0, cents.length - 2);
    if (cents.substring(cents.length - 2) !== '00') {
        amount = amount + '.' + cents.substring(cents.length - 2);
    }

    var linked_note = Autolinker.link(note, {
        replaceFn: function(autolinker, match) {
            switch (match.getType()) {
                case 'url':
                    if (match.getUrl().indexOf('youtu.be/') !== -1 || match.getUrl().indexOf('youtube.com/watch?') !== -1) {
                        var tag = autolinker.getTagBuilder().build(match);
                        tag.addClass('youtube-link');
                        return tag;
                    }
                    return true;
            }
        }
    });

    $div = $('<div>', {'class': 'item'});
    $('#donationlist').prepend($div);
    $image_div = $('<div>', {'class': 'ui tiny image'});
    $div.append($image_div);
    $img = $('<img>', {'src': avatar});
    $image_div.append($img);
    $content_div = $('<div>', {'class': 'content'});
    $div.append($content_div);
    $header_div = $('<div>', {'class': 'header'}).text(username + ' (' + amount + ')');
    $content_div.append($header_div);
    $meta_div = $('<div>', {'class': 'meta'}).text('2 minutes ago'); // XXX: Fix this
    $content_div.append($meta_div);
    $description_div = $('<div>', {'class': 'description'});
    $content_div.append($description_div);
    $description = $('<p>').html(linked_note);
    $description_div.append($description);

    $div.find('.youtube-link').wrap('<div class="youtube-link-wrapper"></div>');
    $div.find('.youtube-link-wrapper').each(function(index, el) {
        var link = $(el).find('a')[0];
        if (link.href !== undefined) {
            console.log(link.href);
            var parsed_uri = parseUri(link.href);
            console.log(parsed_uri);
            var youtube_id = ''
            if (parsed_uri.host.indexOf('youtu.be') !== -1) {
                youtube_id = parsed_uri.path.substring(1);
            } else if (parsed_uri.host.indexOf('youtube.com') !== -1) {
                youtube_id = parsed_uri.queryKey.v;
            }
            var $button = $('<button>', {'class': 'ui small button', 'style': 'padding: 5px;'}).text('Add to pleblist');
            $button.api({
                action: 'pleblist_add_song',
                method: 'post',
                data: {
                    'password': secret_password,
                    'youtube_id': youtube_id,
                },
                beforeSend: function(settings) {
                    settings.data.password = secret_password;
                    return settings;
                }
            }).state({
                onActivate: function() {
                    $button.addClass('disabled green');
                },
                text: {
                    inactive: 'Add to pleblist',
                    active: 'Added!',
                }
            });
            $(el).append($button);
        }
    });
}

function streamtip_connect(access_token)
{
    $.post('/api/v1/streamtip/validate', { 'access_token': access_token }).done(function(data) {
        $('#notification').text('Successfully validated with streamtip');
        secret_password = data.password;

        get_donations(streamtip_client_id, access_token, function(donations, raw_json) {
            donations.reverse();
            for (tip_id in donations) {
                var tip = donations[tip_id];
                add_tip(tip.username, tip.user.avatar, tip.cents, tip.note);
            }
        }, 10, 0);
    }).fail(function(data) {
        $('#notification').text('Unable to validate with this streamtip. Contact pajlada if you believe this is wrong.');
    });
    var socket = io.connect('https://streamtip.com', {
            query: 'access_token='+encodeURIComponent(access_token)
            });

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

    socket.on('newTip', function(data) {
        add_tip(data.username, data.user.avatar, data.cents, data.note);
    });
}

function add_tests()
{
    var tip = {
                "cents" : 10000,
                "user" : {
                    "_id" : "5456997a68db94ce04a5f4c3",
                    "avatar" : "https://static-cdn.jtvnw.net/jtv_user_pictures/2o3a-profile_image-208599ad8e074285-300x300.png",
                    "displayName" : "Test",
                    "name" : "test",
                    "provider" : "twitch",
                    "providerId" : 10101
                },
                "note" : "For the pleblist google.com ab c d e youtu.be/LcySqK5FP6U?omg g f d e www.youtube.com/watch?v=KBVY-uB-wTA",
                "processor" : "PayPal",
                "transactionId" : "4K2N0D835234BWKC",
                "username" : "2o3a"
            };
    add_tip(tip.username, tip.user.avatar, tip.cents, tip.note);
    tip = {
                "cents" : 6969,
                "user" : {
                    "_id" : "5456997a68db94ce04a5f4c3",
                    "avatar" : "https://static-cdn.jtvnw.net/jtv_user_pictures/zombernatural-profile_image-b0d75dded4d8f23a-300x300.png",
                    "displayName" : "Test",
                    "name" : "test",
                    "provider" : "twitch",
                    "providerId" : 10101
                },
                "note" : "youtube.com 4Head",
                "processor" : "PayPal",
                "transactionId" : "4K2N0D835234BWKC",
                "username" : "Zombernatural"
            };
    add_tip(tip.username, tip.user.avatar, tip.cents, tip.note);
    tip = {
                "cents" : 350,
                "user" : {
                    "_id" : "5456997a68db94ce04a5f4c3",
                    "avatar" : "https://static-cdn.jtvnw.net/jtv_user_pictures/zombernatural-profile_image-b0d75dded4d8f23a-300x300.png",
                    "displayName" : "Test",
                    "name" : "test",
                    "provider" : "twitch",
                    "providerId" : 10101
                },
                "note" : "youtube.com 4Head",
                "processor" : "PayPal",
                "transactionId" : "4K2N0D835234BWKC",
                "username" : "Zombernatural"
            };
    add_tip(tip.username, tip.user.avatar, tip.cents, tip.note);
}

$(document).ready(function() {
    function use_access_token_from_hash()
    {
        var hash = window.location.hash.substring(1);

        window.location.hash = '';

        if (hash.length > 2) {
            streamtip_connect(hash);
            return true;
        }

        return false;
    }

    add_tests();

    var res = use_access_token_from_hash();
    if (res == true) {
        var $p = $('<p>').text('Logged in with streamtip!');
        $('#button_div').append($p);
    } else {
        var $button = $('<button>', {'class': 'ui button', 'onclick': 'streamtip_auth()'}).text('Log in with Streamtip');
        $('#button_div').append($button);
    }
});

