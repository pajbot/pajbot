function testtip(message)
{
    if (message === undefined) {
        message = 'Hello, I hope this works Kappa. forsenW';
    }

    show_tip('fake user', '5', '$', message, widget_type);
}

function testlong()
{
    var msg = 'Hello, I hope this works Kappa. forsenW! Hello, I hope this works Kappa. forsenW! Hello, I hope this works Kappa. forsenW! Hello, I hope this works Kappa. forsenW! Hello, I hope this works Kappa.';

    show_tip('test_long', '5', '$', msg, widget_type);
}

function teststrange()
{
    var msg = 'kalsdfyuasdf98723985423$%@^oipa[{}asiodf798^*&^&*#$@#Uih234ui23h4iu23h4iIUIZIISWWWWWWWWWWWWWWWWWWWWWWwwwwwwwwwwjlkjdglksdgsdoiio9z876&*^*&&******&^*&^FSUHFEKJRwkjerhwjerhsljdfhgksjdfghskdlfjghsdkgwwll';
    show_tip('test_trange', '5', '$', msg, widget_type);
}

function escapeRegExp(str) {
    return str.replace(/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, "\\$&");
}

function show_tip(user, amount, symbol, note, type, condition, style)
{
    if (condition === undefined) {
        condition = 'default';
    }
    if (style === undefined) {
        style = '0';
    }

    if (timer) {
        clearTimeout(timer);
    }

    var condition_id = 0;
    for (var i in conditions) {
        if (condition == conditions[i].index) {
            condition_id = i;
            console.log('FOUND IT XD');
            break;
        }
    }
    console.log(conditions);
    console.log('Condition: ' + condition);
    console.log('Style: ' + style);
    var sound = conditions[condition_id].styles[style].sound;

    if (sound.enabled) {
        setTimeout(function() {
            sound.audio.play();
        }, sound.delay);
    }
    
    var original_note = note;

    /* Strip donation message and username of HTML tags */
    note = $('<div/>').html(note).text();
    user = $('<div/>').html(user).text();

    if (typeof emotes !== 'undefined') {
        /* TODO: preload commonly used emotes */
        $.each(emotes, function(code, emote) {
            if (emote.i !== null) {
                var replacement = '<img class="emote" src="//static-cdn.jtvnw.net/emoticons/v1/'+emote.i+'/3.0"/>';
            } else if (emote.h !== null) {
                var replacement = '<img class="emote" src="//cdn.betterttv.net/emote/'+emote.h+'/3x"/>';
            } else {
                return;
            }
            note = note.replace(new RegExp(escapeRegExp(code), 'g'), replacement);
        });
    }
    amount = +(parseFloat(amount)).toFixed(2);
    if (type == 'basic') {
        $("#new-tip .note").html(user + ' (' + symbol + amount + '): ' + note);
    } else {
        $("#new-tip").text(symbol+amount+' from '+user);
        $("#new-tip-note").html(note);
    }
    $('#tip-alert').removeClass();
    $('#tip-alert').addClass(type + ' c' + condition + ' s' + style);
    $("#tip-alert").fadeIn("slow", function() {
        // do nothing
    });
    timer = setTimeout(function() {
        $("#tip-alert").fadeOut("slow");
    }, 10000);

    if (use_tts) {
        tts_message(original_note);
    }
}

var tts_sound = null;

function tts_message(message)
{
    if (tts_endpoint == '') {
        return;
    }
    var voice = 'en-US_LisaVoice';
    var voice = 'en-GB_KateVoice';
    var voice = 'en-US_AllisonVoice';
    message = message.replace(new RegExp('#', 'g'), 'hashtag');
    message = message.replace(new RegExp('<3', 'g'), ' love ');
    var tts_url = tts_endpoint + '?voice=' + voice + '&text=' + encodeURI(message) + '&token=' + tts_authorization;

    tts_sound = new Audio();
    tts_sound.addEventListener('playing', function() {
        console.log('tts playing = true');
        tts_playing = true;
    });
    tts_sound.addEventListener('ended', function() {
        console.log('tts playing = false');
        tts_playing = false;
        tts_sound = null;
    });
    tts_sound.src = tts_url;
    tts_sound.load();
    tts_sound.play();
}

function getParameterByName(name)
{
    name = name.replace(/[\[]/, "\\\[").replace(/[\]]/, "\\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
        results = regex.exec(location.search);
    return results == null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
}

function begin_load()
{
    /* This function is called once everything is finished */
}

cool_socket = null;

function connect_to_cool_socket_io_thing()
{
    return;
    cool_socket = io('wss://pajlada.se:2351/clr');

    cool_socket.on('skip', function() {
        tts_playing = false;
        if (tts_sound !== null) {
            console.log('Stopping current TTS sound.');
            tts_sound.pause();
        } else {
            console.log('No tts to skip atm.');
        }
    });
}

authenticated = false;
document_ready = false;

function on_authenticated()
{
    console.log('on_authenticated ;O');
    authenticated = true;
    if (document_ready == true) {
        begin_load();
    }
}

$(document).ready(function() {
    connect_to_cool_socket_io_thing();
    document_ready = true;
    if (authenticated == true) {
        begin_load();
    }
});
