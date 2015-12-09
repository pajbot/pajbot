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

    var youtube_link_el = $div.find('.youtube-link');
    youtube_link_el.wrap('<div class="youtube-link-wrapper ui segment loading"></div>');
    $div.find('.youtube-link-wrapper').each(function(index, el) {
        var link = $(el).find('a')[0];
        if (link.href !== undefined) {
            var parsed_uri = parseUri(link.href);
            var youtube_id = parse_youtube_id_from_url(link.href);
            var song_info = null;
            if (youtube_id !== false) {
                $.api({
                    action: 'pleblist_validate',
                    method: 'post',
                    on: 'now',
                    data: {
                        'youtube_id': youtube_id,
                    },
                    onComplete: function(response, element, xhr) {
                        $(el).removeClass('loading');
                    },
                    onSuccess: function(response, element, xhr) {
                        if (response.new_youtube_id !== undefined) {
                            youtube_id = response.new_youtube_id;
                        }
                        youtube_link_el.html('youtu.be/'+youtube_id+'&emsp;');
                        song_info = response.song_info;
                        if (song_info !== null) {
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
                            var $data = $('<div>').text('Song title: ' + song_info.title);
                            $(el).append($data);
                            var $data = $('<div>').text('Song length: ' + moment.duration(song_info.duration, 'seconds').format('h:mm:ss'));
                            $(el).append($data);
                        } else {
                            var $button = $('<button>', {'class': 'ui small button red disabled', 'style': 'padding: 5px;'}).text('Invalid youtube link');
                            $(el).append($button);
                        }
                    }
                });
            }
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
                "note" : "youtube.com 4Head youtu.be/abcdefghijkKappa",
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
                "note" : "youtube.com 4Head for the pleblist xD https://youtu.be/uXFQPfQVT4QKappa",
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

    //add_tests();

    var res = use_access_token_from_hash();
    if (res == true) {
        var $p = $('<p>').text('Logged in with streamtip!');
        $('#button_div').append($p);
    } else {
        var $button = $('<button>', {'class': 'ui button', 'onclick': 'streamtip_auth()'}).text('Log in with Streamtip');
        $('#button_div').append($button);
    }
});

