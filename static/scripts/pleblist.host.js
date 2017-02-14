var secret_password = undefined;
var currency_symbols = {
    'USD': '$', // US Dollar
    'EUR': '€', // Euro
    'CRC': '₡', // Costa Rican Colón
    'GBP': '£', // British Pound Sterling
    'ILS': '₪', // Israeli New Sheqel
    'INR': '₹', // Indian Rupee
    'JPY': '¥', // Japanese Yen
    'KRW': '₩', // South Korean Won
    'NGN': '₦', // Nigerian Naira
    'PHP': '₱', // Philippine Peso
    'PLN': 'zł', // Polish Zloty
    'PYG': '₲', // Paraguayan Guarani
    'THB': '฿', // Thai Baht
    'UAH': '₴', // Ukrainian Hryvnia
    'VND': '₫', // Vietnamese Dong
};

function add_tip(username, avatar, amount, cents, note, currency_symbol)
{
    if (currency_symbol == null) {
        currency_symbol = '$';
    }

    if (amount == null) {
        cents = String(cents);
        amount = cents.substring(0, cents.length - 2);
        if (cents.substring(cents.length - 2) !== '00') {
            amount = amount + '.' + cents.substring(cents.length - 2);
        }
    }

    var linked_note = Autolinker.link(note, {
        replaceFn: function(autolinker, match) {
            switch (match.getType()) {
                case 'url':
                    var parsed_uri = parseUri(match.getUrl());
                    if (match.getUrl().indexOf('youtu.be/') !== -1 || match.getUrl().indexOf('youtube.com/watch?') !== -1) {
                        var tag = autolinker.getTagBuilder().build(match);
                        tag.addClass('youtube-link');
                        return tag;
                    } else if (parsed_uri.host.endsWith('imgur.com') === true) {
                        var tag = autolinker.getTagBuilder().build(match);
                        tag.addClass('imgur-link');
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
    $header_div = $('<div>', {'class': 'header'}).text(username + ' (' + currency_symbol + amount + ')');
    $content_div.append($header_div);
    /*
    $meta_div = $('<div>', {'class': 'meta'}).text(';)'); // XXX: Fix this
    $content_div.append($meta_div);
    */
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
            console.log('[Pleblist Host] Checking ' + link.href);
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
                        var youtube_url = 'youtu.be/'+youtube_id;
                        $(el).find('.youtube-link').html(youtube_url+'&emsp;').attr('href', 'https://'+youtube_url);
                        song_info = response.song_info;
                        if (song_info !== null) {
                            var $button = $('<button>', {'class': 'ui small button playfull', 'style': 'padding: 5px;'}).text('Add to pleblist');;
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
                                },
                                onSuccess: function(response, element, xhr) {
                                    $(element).parent().find('button.skipafter6').hide();
                                    $(element).parent().find('button.skipafter10').hide();
                                }
                            }).state({
                                onActivate: function() {
                                    $button.addClass('disabled green');
                                    $button.removeClass('black');
                                },
                                text: {
                                    inactive: 'Add to pleblist',
                                    active: 'Added!',
                                }
                            });
                            $(el).append($button);
                            if (song_info.duration > 6 * 60) {
                                var $skip_after_6 = $('<button>', {'class': 'black ui small button skipafter6', 'style': 'padding: 5px;'}).html('Play 6 minutes');
                                $skip_after_6.api({
                                    action: 'pleblist_add_song',
                                    method: 'post',
                                    data: {
                                        'password': secret_password,
                                        'youtube_id': youtube_id,
                                        'skip_after': 6 * 60,
                                    },
                                    beforeSend: function(settings) {
                                        settings.data.password = secret_password;
                                        return settings;
                                    },
                                    onSuccess: function(response, element, xhr) {
                                        $(element).parent().find('button.playfull').hide();
                                        $(element).parent().find('button.skipafter10').hide();
                                    }
                                }).state({
                                    onActivate: function() {
                                        $skip_after_6.addClass('disabled green');
                                        $skip_after_6.removeClass('black');
                                    },
                                    text: {
                                        inactive: 'Play 6 minutes',
                                        active: 'Added!',
                                    }
                                });
                                $(el).append($skip_after_6);
                            }
                            if (song_info.duration > 10 * 60) {
                                var $skip_after_10 = $('<button>', {'class': 'black ui small button skipafter10', 'style': 'padding: 5px;'}).html('Play 10 minutes');
                                $skip_after_10.api({
                                    action: 'pleblist_add_song',
                                    method: 'post',
                                    data: {
                                        'password': secret_password,
                                        'youtube_id': youtube_id,
                                        'skip_after': 10 * 60,
                                    },
                                    beforeSend: function(settings) {
                                        settings.data.password = secret_password;
                                        return settings;
                                    },
                                    onSuccess: function(response, element, xhr) {
                                        $(element).parent().find('button.playfull').hide();
                                        $(element).parent().find('button.skipafter6').hide();
                                    }
                                }).state({
                                    onActivate: function() {
                                        $skip_after_10.addClass('disabled green');
                                        $skip_after_10.removeClass('black');
                                    },
                                    text: {
                                        inactive: 'Play 10 minutes',
                                        active: 'Added!',
                                    }
                                });
                                $(el).append($skip_after_10);
                            }
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

    var imgur_link_el = $div.find('.imgur-link');
    imgur_link_el.wrap('<div class="imgur-link-wrapper ui segment"></div>');
    $div.find('.imgur-link-wrapper').each(function(index, el) {
        var link = $(el).find('a')[0];
        if (link.href !== undefined) {
            var parsed_uri = parseUri(link.href);
            var imgur_data = parse_imgur_data_from_url(parsed_uri);
            if (imgur_data.id !== false) {
                if (imgur_data.album === true) {
                    var $data = $('<span>', {'style': 'padding-left: 15px;'}).html('<strong>ALBUM</strong>, can contain gifs.');
                    $(el).append($data);
                }
                if (imgur_data.new_url !== false) {
                    // Replace the link
                    link.href = imgur_data.new_url;
                }
            }
        }
    });
}

$(document).ready(function() {
    secret_password = $.cookie('password');

    function successful_login(res)
    {
        var $btn = $('#button_div button.' + res.toLowerCase());
        $btn.addClass('green');
        $btn.text('Logged in with ' + res);
    }

    var services = {
        'Streamtip': {
            cookie: 'streamtip_access_token',
            connect_method: streamtip_connect,
        },
        'StreamElements': {
            cookie: 'streamelements_access_token',
            connect_method: streamelements_connect,
        },
        'Streamlabs': {
            cookie: 'streamlabs_access_token',
            connect_method: streamlabs_connect,
        },
    };

    $.each(services, function(name, data) {
        if ($.cookie(data.cookie)) {
            data.connect_method($.cookie(data.cookie));
            $.removeCookie(data.cookie, { path: '/' });
            successful_login(name);
        }
    });
});

