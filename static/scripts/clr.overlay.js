if (!String.prototype.format) {
  String.prototype.format = function() {
    var args = arguments;
    return this.replace(/{(\d+)}/g, function(match, number) {
      return typeof args[number] != 'undefined'
        ? args[number]
        : match
      ;
    });
  };
}
samples = {
    'bossofthisgym': { 'url': 'http://soundboard.ass-we-can.com/static/music/MarkW/Boss of this gym.mp3', },
    'fuckyou': { 'url': 'http://soundboard.ass-we-can.com/static/music/VanD/FUCKYOU.mp3' },
    'idontdoanal': { 'url': 'http://soundboard.ass-we-can.com/static/music/VanD/I don\'t do anal.mp3' },
    'knock': { 'url': 'http://www.audiocheck.net/Audio/audiocheck.net_binaural_knocking.mp3' },
    'slap': { 'url': 'https://pajlada.se/files/clr/slap.mp3' },
    'cumming': { 'url': 'http://soundboard.ass-we-can.com/static/music/VanD/Fucking%20cumming.mp3' }
    'collegeboy': { 'url': 'http://soundboard.ass-we-can.com/static/music/BillyH/Come%20on%20college%20boy.mp3' }
    'oooh': { 'url': 'http://soundboard.ass-we-can.com/static/music/VanD/Penetration%204.mp3' }
    'suction': { 'url': 'http://soundboard.ass-we-can.com/static/music/VanD/Suction.mp3' }
};
$(document).ready(function() {
    connect_to_ws();
    for (var key in samples) {
        sample = samples[key];
        sample['audio'] = new Audio(sample['url']);
    }
});

var isopen = false;
var ws_host = 'wss://pajlada.se';
var ws_port = '2320';

function add_random_box(color)
{
    var numRand = Math.floor(Math.random() * 501);
    var divsize = 50;
    var posx = (Math.random() * ($(document).width() - divsize)).toFixed();
    var posy = (Math.random() * ($(document).height() - divsize)).toFixed();
    var $newdiv = $("<div class='exploding'></div>").css({
        'left': posx + 'px',
        'top': posy + 'px',
        'background-color': color,
        'opacity': 0
    });
    $newdiv.appendTo('body');
    $newdiv.animate({
        opacity: 1
    }, 500);
    setTimeout(function() {
        $newdiv.animate({
            opacity: 0,
        }, 1000);
        setTimeout(function() {
            $newdiv.remove();
        }, 1000);
    }, 5000);
}

function add_emote(emote)
{
    var url = '';
    if ('bttv_hash' in emote) {
        url = 'https://cdn.betterttv.net/emote/' + emote['bttv_hash'] + '/3x';
    } else {
        url = 'https://static-cdn.jtvnw.net/emoticons/v1/' + emote['twitch_id'] + '/3.0';
    }
    var numRand = Math.floor(Math.random() * 501);
    var divsize = 120;
    var posx = (Math.random() * ($(document).width() - divsize)).toFixed();
    var posy = (Math.random() * ($(document).height() - divsize)).toFixed();
    var $newdiv = $('<img class="absemote" src="' + url + '">').css({
        'left': posx + 'px',
        'top': posy + 'px',
        'opacity': 0
    });
    $newdiv.appendTo('body');
    $newdiv.animate({
        opacity: 1
    }, 500);
    setTimeout(function() {
        $newdiv.animate({
            opacity: 0,
        }, 1000);
        setTimeout(function() {
            $newdiv.remove();
        }, 1000);
    }, 5000);
}

var message_id = 0;

function add_notification(message)
{
    var new_notification = $('<div>' + message + '</div>').prependTo('div.notifications');
    new_notification.textillate({
        autostart: false,
        in: {
            effect: 'bounceInLeft',
            delay: 5,
            delayScale: 1.5,
            sync: false,
            shuffle: false,
            reverse: false,
        },
        out: {
            effect: 'bounceOutLeft',
            sync: true,
            shuffle: false,
            reverse: false,
        },
        type: 'word',
    });
    new_notification.on('inAnimationEnd.tlt', function() {
        setTimeout(function() {
            new_notification.textillate('out');
            new_notification.animate({
                height: 0,
                opacity: 0,
            }, 1000);
        }, 2000);
    });
    new_notification.on('outAnimationEnd.tlt', function() {
        setTimeout(function() {
            new_notification.remove();
        }, 250);
    });
}

var current_emote_code = null;
var close_down_combo = null;

function refresh_combo_count(count)
{
    $('#emote_combo span.count').html(count);
    $('#emote_combo span.count').addClass('animated pulsebig');
    $('#emote_combo span.count').on('webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend', function() {
        $(this).removeClass('animated pulsebig');
    });
    $('#emote_combo img').addClass('animated pulsebig');
    $('#emote_combo img').on('webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend', function() {
        $(this).removeClass('animated pulsebig');
    });
}

function refresh_combo_emote(emote)
{
    console.log(emote);
    if ('bttv_hash' in emote && emote['bttv_hash'] !== null) {
        var url = 'https://cdn.betterttv.net/emote/' + emote['bttv_hash'] + '/2x';
    } else {
        var url = 'https://static-cdn.jtvnw.net/emoticons/v1/' + emote['twitch_id'] + '/2.0';
    }
    $('#emote_combo img').attr('src', url);
}

function debug_text(text)
{
    //add_notification(text);
}

function refresh_emote_combo(emote, count)
{
    var emote_combo = $('#emote_combo');
    if (emote_combo.length == 0) {
        if ('bttv_hash' in emote && emote['bttv_hash'] !== null) {
            var url = 'https://cdn.betterttv.net/emote/' + emote['bttv_hash'] + '/2x';
        } else {
            var url = 'https://static-cdn.jtvnw.net/emoticons/v1/' + emote['twitch_id'] + '/2.0';
        }
        current_emote_code = emote['code'];
        var message = 'x<span class="count">{0}</span> <img class="comboemote" src="{1}" /> combo!'.format(count, url)
        var new_notification = $('<div id="emote_combo">' + message + '</div>').prependTo('div.notifications');
        new_notification.addClass('animated bounceInLeft');

        new_notification.on('webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend', function() {
            if (new_notification.hasClass('ended')) {
                new_notification.animate({
                    height: 0,
                    opacity: 0,
                }, 500);
                setTimeout(function() {
                    new_notification.remove();
                }, 500);
            }
        });

        clearTimeout(close_down_combo);
        close_down_combo = setTimeout(function() {
            new_notification.addClass('animated bounceOutLeft ended');
        }, 4000);
    } else {
        clearTimeout(close_down_combo);
        close_down_combo = setTimeout(function() {
            emote_combo.addClass('animated bounceOutLeft ended');
        }, 3000);
        refresh_combo_emote(emote);
        refresh_combo_count(count);
    }
}

function play_sound(sample)
{
    sample = sample.toLowerCase();
    if (sample in samples) {
        samples[sample]['audio'].cloneNode().play();
    }
}

function connect_to_ws()
{
    if (isopen) {
        return;
    }
    console.log('Connecting to websocket....');
    var host = ws_host;
    var port = ws_port;
    socket = new WebSocket(host + ':' + port);
    socket.binaryType = "arraybuffer";
    socket.onopen = function() {
        console.log('Connected!');
        isopen = true;
    }

    socket.onmessage = function(e) {
        if (typeof e.data == "string") {
            var json_data = JSON.parse(e.data);
            console.log(json_data);
            if (json_data['event'] !== undefined) {
                switch (json_data['event']) {
                    case 'new_box':
                        add_random_box(json_data['data']['color']);
                        break;
                    case 'new_emote':
                        add_emote(json_data['data']['emote']);
                        break;
                    case 'timeout':
                        add_notification('<span class="user">' + json_data['data']['user'] + '</span> timed out <span class="victim">' + json_data['data']['victim'] + '</span> EleGiggle');
                        setTimeout(function() {
                            play_sound('slap');
                        }, 100);
                        break;
                    case 'play_sound':
                        play_sound(json_data['data']['sample']);
                        break;
                    case 'emote_combo':
                        refresh_emote_combo(json_data['data']['emote'], json_data['data']['count']);
                        break;
                }
            }
        } else {
            var arr = new Uint8Array(e.data);
            var hex = '';
            for (var i = 0; i < arr.length; i++) {
                hex += ('00' + arr[i].toString(16)).substr(-2);
            }
            //add_row('Binary message received: ' + hex);
        }
    }

    socket.onclose = function(e) {
        socket = null;
        isopen = false;
        setTimeout(connect_to_ws, 2500);
    }
}
