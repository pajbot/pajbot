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
    'idontdoanal': { 'url': 'https://pajlada.se/files/clr/i_dont_do_anal.mp3' },
    'knock': { 'url': 'https://pajlada.se/files/clr/knock.mp3' },
    'slap': { 'url': 'https://pajlada.se/files/clr/slap.mp3' },
    'cumming': { 'url': 'https://pajlada.se/files/clr/cumming.mp3' },
    'collegeboy': { 'url': 'http://soundboard.ass-we-can.com/static/music/BillyH/Come%20on%20college%20boy.mp3' },
    'oooh': { 'url': 'https://pajlada.se/files/clr/oooh.mp3' },
    'suction': { 'url': 'https://pajlada.se/files/clr/suction.mp3' },
    'takeit': { 'url': 'http://soundboard.ass-we-can.com/static/music/VanD/Take%20it%20boy.mp3' },
    'amazing': { 'url': 'http://soundboard.ass-we-can.com/static/music/VanD/That\'s%20amazing.mp3' },
    'power': { 'url': 'https://pajlada.se/files/clr/power.mp3' },
    'othernight': { 'url': 'https://pajlada.se/files/clr/othernight.mp3' },
    'asswecan': { 'url': 'https://pajlada.se/files/clr/ass_we_can.mp3' },
    'lashofthespanking': { 'url': 'http://soundboard.ass-we-can.com/static/music/BillyH/Lash%20of%20the%20spanking.mp3' },
    'nyanpass': { 'url': 'https://pajlada.se/files/clr/nyanpass.mp3' },
    'scamazishere': { 'url': 'https://pajlada.se/files/clr/scamaz_is_here.mp3' },
    'lul': { 'url': ['https://pajlada.se/files/clr/LUL.mp3', 'https://pajlada.se/files/clr/LUL-02.mp3'] },
    'ohmyshoulder': { 'url': 'https://pajlada.se/files/clr/ohmyshoulder.mp3' },
    'tuturu': { 'url': 'https://pajlada.se/files/clr/tuturu.mp3' },
    'attention': { 'url': 'https://pajlada.se/files/clr/attention.mp3' },
    'aaaah': { 'url': 'https://pajlada.se/files/clr/AAAAAAAH.mp3' },
    'jesse': { 'url': 'https://pajlada.se/files/clr/jesse-cook.mp3' },
    'shakalaka': { 'url': 'https://pajlada.se/files/clr/shakalaka.mp3' },
    'loan': { 'url': 'https://pajlada.se/files/clr/its_a_loan.mp3' },
    'spankmoan1': { 'url': 'https://pajlada.se/files/clr/spankmoan1.mp3' },
    'youlikechallenges': { 'url': 'https://pajlada.se/files/clr/you_like_challenges.mp3' },
    'youlikethat': { 'url': 'https://pajlada.se/files/clr/you_like_that.mp3' },
    'pants': { 'url': 'https://pajlada.se/files/clr/ripped_pants.mp3' },
    'oh': { 'url': 'https://pajlada.se/files/clr/oh.mp3' },
    'poi': { 'url': 'https://pajlada.se/files/clr/poi.mp3' },
    'ayaya': { 'url': 'https://pajlada.se/files/clr/ayaya.mp3' },
    'car': { 'url': 'https://pajlada.se/files/clr/car.mp3' },
    'dayum': { 'url': 'https://pajlada.se/files/clr/dayum.mp3' },
    'water': { 'url': 'https://pajlada.se/files/clr/water1.mp3' },
    'doitdad': { 'url': 'https://pajlada.se/files/clr/do_it_dad.mp3' },
    'face': { 'url': 'https://pajlada.se/files/clr/me_go_face.mp3' },
    'sike': { 'url': 'https://pajlada.se/files/clr/sike.mp3' },
    'yahallo': { 'url': 'https://pajlada.se/files/clr/yahallo.mp3' },
    'djkarlthedog': { 'url': 'https://pajlada.se/files/clr/djkarlthedog.mp3' },
    'bomblobber': { 'url': 'https://pajlada.se/files/clr/bomb_lobber.mp3' },
    'baka': { 'url': 'https://pajlada.se/files/clr/baka.mp3' },
    'march': { 'url': 'https://pajlada.se/files/clr/march.mp3' },
    'embarrassing': { 'url': 'https://pajlada.se/files/clr/embarrassing.mp3' },
    'yessir': { 'url': 'https://pajlada.se/files/clr/yes_sir.mp3' },
    'sixhotloads': { 'url': 'https://pajlada.se/files/clr/six_hot_loads.mp3' },
    'wrongnumba': { 'url': 'https://pajlada.se/files/clr/wrong_numba.mp3' },
    'sorry': { 'url': 'https://pajlada.se/files/clr/sorry.mp3' },
    'relax': { 'url': 'https://pajlada.se/files/clr/relax.mp3' },
    'vibrate': { 'url': 'https://pajlada.se/files/clr/vibrate.mp3' },
    '4head': { 'url': 'https://pajlada.se/files/clr/4Head.mp3' },
    'akarin': { 'url': ['https://pajlada.se/files/clr/akarin.mp3', 'https://pajlada.se/files/clr/akarin-02.mp3'] },
    'behindyou': { 'url': 'https://pajlada.se/files/clr/behindyou.mp3' },
    'bitch': { 'url': 'https://pajlada.se/files/clr/bitch.mp3' },
    'damnson': { 'url': 'https://pajlada.se/files/clr/damnson.mp3' },
    'desu': { 'url': 'https://pajlada.se/files/clr/desu.mp3' },
    'fatcock': { 'url': 'https://pajlada.se/files/clr/fatcock.mp3' },
    'gangingup': { 'url': 'https://pajlada.se/files/clr/gangingup.mp3' },
    'iseeyou1': { 'url': 'https://pajlada.se/files/clr/iseeyou1.mp3' },
    'iseeyou2': { 'url': 'https://pajlada.se/files/clr/iseeyou2.mp3' },
    'jeff': { 'url': 'https://pajlada.se/files/clr/jeff.mp3' },
    'mistake': { 'url': 'https://pajlada.se/files/clr/mistake.mp3' },
    'ohbabyatriple': { 'url': 'https://pajlada.se/files/clr/ohbabyatriple.mp3' },
    'rin': { 'url': 'https://pajlada.se/files/clr/rin.mp3' },
    'sheeeit': { 'url': 'https://pajlada.se/files/clr/sheeeit.mp3' },
    'spook': { 'url': 'https://pajlada.se/files/clr/spook.mp3' },
    'surprise': { 'url': 'https://pajlada.se/files/clr/surprise.mp3' },
    'tuckfrump': { 'url': 'https://pajlada.se/files/clr/tuckfrump.mp3' },
    'uguu': { 'url': 'https://pajlada.se/files/clr/uguu.mp3' },
    'weed': { 'url': 'https://pajlada.se/files/clr/weed.mp3' },
    'wrongdoor': { 'url': 'https://pajlada.se/files/clr/wrongdoor.mp3' },
    'ryuu': { 'url': 'https://pajlada.se/files/clr/hanzo.mp3' },
    'yeehaw': { 'url': 'https://pajlada.se/files/clr/yeehaw.mp3' },
};
$(document).ready(function() {
    connect_to_ws();
    for (var key in samples) {
        sample = samples[key];
        var all_samples = [].concat(sample['url']);
        console.log(all_samples);
        sample['audio'] = [];
        for (url in all_samples) {
            sample['audio'].push(new Audio(all_samples[url]));
        }
    }
});

var isopen = false;

function add_random_box(color)
{
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
    if ('bttv_hash' in emote && emote['bttv_hash'] !== null) {
        url = 'https://cdn.betterttv.net/emote/' + emote['bttv_hash'] + '/3x';
    } else if ('ffz_id' in emote && emote['ffz_id'] !== null) {
        url = 'http://cdn.frankerfacez.com/emoticon/' + emote['ffz_id'] + '/4';
    } else if ('twitch_id' in emote) {
        url = 'https://static-cdn.jtvnw.net/emoticons/v1/' + emote['twitch_id'] + '/3.0';
    } else {
        if (emote['code'] == 'xD') {
            url = 'https://cdn.pajlada.se/emoticons/XD.gif';
        }
    }
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

function show_custom_image(data)
{
    var url = data.url;
    var divsize = 120;
    var posx = (Math.random() * ($(document).width() - divsize)).toFixed();
    var posy = (Math.random() * ($(document).height() - divsize)).toFixed();
    var css_data = {
        'left': posx + 'px',
        'top': posy + 'px',
        'opacity': 0
    }
    if (data.width !== undefined) {
        css_data.width = data.width;
    }
    if (data.height !== undefined) {
        css_data.height = data.height;
    }
    if (data.x !== undefined) {
        css_data.left = data.x + 'px';
    }
    if (data.y !== undefined) {
        css_data.top = data.y + 'px';
    }
    var $newdiv = $('<img class="absemote" src="' + url + '">').css(css_data);
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
    var url = '';
    if ('bttv_hash' in emote && emote['bttv_hash'] !== null) {
        url = 'https://cdn.betterttv.net/emote/' + emote['bttv_hash'] + '/3x';
    } else if ('ffz_id' in emote && emote['ffz_id'] !== null) {
        url = 'http://cdn.frankerfacez.com/emoticon/' + emote['ffz_id'] + '/4';
    } else if ('twitch_id' in emote) {
        url = 'https://static-cdn.jtvnw.net/emoticons/v1/' + emote['twitch_id'] + '/3.0';
    } else {
        if (emote['code'] == 'xD') {
            url = 'https://cdn.pajlada.se/emoticons/XD.gif';
        }
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

function create_object_for_win(points)
{
    return {
        value: points,
        color: '#64DD17',
    }
}

function create_object_for_loss(points)
{
    return {
        value: points,
        color: '#D50000',
    }
}

var hsbet_chart = false;

function hsbet_set_data(win_points, loss_points) {
    if (hsbet_chart !== false) {
        hsbet_chart.segments[0].value = win_points;
        hsbet_chart.segments[1].value = loss_points;
        hsbet_chart.update();
    }
}

function hsbet_update_data(win_points, loss_points) {
    if (hsbet_chart !== false) {
        hsbet_chart.segments[0].value += win_points;
        hsbet_chart.segments[1].value += loss_points;
        hsbet_chart.update();
    }
}

function create_graph(win, loss)
{
    var ctx = $('#hsbet .chart').get(0).getContext('2d');
    if (win == 0) {
        win = 1;
    }
    if (loss == 0) {
        loss = 1;
    }
    var data = [
        create_object_for_win(win),
        create_object_for_loss(loss),
    ];
    var options = {
        animationSteps: 100,
        animationEasing: 'easeInOutQuart',
        segmentShowStroke: false,
    };
    if (hsbet_chart === false || true) {
        hsbet_chart = new Chart(ctx).Pie(data, options);
    } else {
        hsbet_set_data(win, loss);
    }
}

/* interval for ticking down the hsbet timer */
var tick_down = false;
var stop_hsbet = false;
var stop_hsbet_2 = false;

function hsbet_new_game(time_left, win, loss)
{
    console.log(time_left);
    var hsbet_el = $('#hsbet');

    if (tick_down !== false) {
        clearInterval(tick_down);
        clearTimeout(stop_hsbet);
        clearTimeout(stop_hsbet_2);
    }

    time_left -= 10;

    if (time_left <= 0) {
        return;
    }

    var time_left_el = hsbet_el.find('.time_left');
    console.log(time_left_el);
    console.log(time_left_el.text());
    time_left_el.text(time_left);
    console.log(time_left);
    hsbet_el.find('.left').css({'visibility': 'visible', 'opacity': 1});

    hsbet_el.hide();
    tick_down = setInterval(function() {
        console.log('HI');
        var old_val = parseInt(time_left_el.text());
        time_left_el.text(old_val - 1);
    }, 1000);
    stop_hsbet = setTimeout(function() {
        clearInterval(tick_down);
        hsbet_el.find('.left').fadeTo(1000, 0, function() {
            hsbet_el.find('.left').css('visibility', 'hidden');
            //hsbet_chart.update();
        });
        stop_hsbet_2 = setTimeout(function() {
            hsbet_el.fadeOut(1000);
        }, 10000);
    }, time_left * 1000);
    if (hsbet_chart !== false) {
        hsbet_chart.clear();
    }
    hsbet_el.find('.left').show();
    hsbet_el.fadeIn(1000, function() {
        create_graph(win, loss);
        console.log('XD');
    });
}

function play_sound(sample)
{
    sample = sample.toLowerCase();
    if (sample in samples) {
        var r = Math.floor(Math.random() * samples[sample]['audio'].length);
        console.log(r);
        var cloned_sample = samples[sample]['audio'][r].cloneNode();
        console.log(cloned_sample);
        cloned_sample.volume = 0.4;
        cloned_sample.play();
    }
}

function play_custom_sound(url)
{
    var audio = new Audio(url);
    audio.volume = 0.4;
    audio.play();
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
                    case 'notification':
                        add_notification(json_data['data']['message']);
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
                    case 'play_custom_sound':
                        play_custom_sound(json_data['data']['url']);
                        break;
                    case 'emote_combo':
                        refresh_emote_combo(json_data['data']['emote'], json_data['data']['count']);
                        break;
                    case 'hsbet_new_game':
                        hsbet_new_game(json_data['data']['time_left'], json_data['data']['win'], json_data['data']['loss']);
                        break;
                    case 'hsbet_update_data':
                        hsbet_update_data(json_data['data']['win'], json_data['data']['loss']);
                        break;
                    case 'show_custom_image':
                        show_custom_image(json_data['data']);
                        break;
                    case 'refresh':
                    case 'reload':
                        location.reload(true);
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
