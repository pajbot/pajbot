function testtip()
{
    show_tip('fake user', '5', '$', 'Hello, I hope this works Kappa. forsenW');
}

function testlong()
{
    var msg = 'Hello, I hope this works Kappa. forsenW! Hello, I hope this works Kappa. forsenW! Hello, I hope this works Kappa. forsenW! Hello, I hope this works Kappa. forsenW! Hello, I hope this works Kappa.';

    show_tip('test_long', '5', '$', msg);
}

function teststrange()
{
    var msg = 'kalsdfyuasdf98723985423$%@^oipa[{}asiodf798^*&^&*#$@#Uih234ui23h4iu23h4iIUIZIISWWWWWWWWWWWWWWWWWWWWWWwwwwwwwwwwjlkjdglksdgsdoiio9z876&*^*&&******&^*&^FSUHFEKJRwkjerhwjerhsljdfhgksjdfghskdlfjghsdkgwwll';
    show_tip('test_trange', '5', '$', msg);
}

function escapeRegExp(str) {
    return str.replace(/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, "\\$&");
}

function show_tip(user, amount, symbol, note)
{
    if (timer) {
        clearTimeout(timer);
    }

    if (sound.enabled) {
        setTimeout(function() {
            sound.audio.play();
        }, sound.delay);
    }
    
    var original_note = note;

    if (typeof emotes !== 'undefined') {
        /* TODO: preload commonly used emotes */
        $.each(emotes, function(code, emote) {
            if (emote.i !== null) {
                var replacement = '<img style="height:1.2em;margin: -5px 0;" src="//static-cdn.jtvnw.net/emoticons/v1/'+emote.i+'/3.0"/>';
            } else if (emote.h !== null) {
                var replacement = '<img style="height:1.2em;margin: -5px 0;" src="//cdn.betterttv.net/emote/'+emote.h+'/3x"/>';
            } else {
                return;
            }
            note = note.replace(new RegExp(escapeRegExp(code), 'g'), replacement);
        });
    }
    amount = +(parseFloat(amount)).toFixed(2);
    $("#new-tip").html(symbol+amount+' from '+user);
    $("#new-tip-note").html(note);
    $("#tip-alert").fadeIn("slow", function() {
        // do nothing
    });
    timer = setTimeout(function() {
        $("#tip-alert").fadeOut("slow");
    }, 10000);

    console.log(use_tts);

    if (use_tts) {
        tts_message(original_note);
    }
}

var tts_sound = null;

function tts_message(message)
{
    var voice = 'en-US_LisaVoice';
    var voice = 'en-GB_KateVoice';
    var voice = 'en-US_AllisonVoice';
    //message = 'gachiGASM';
    console.log(tts_authorization);
    message = message.replace('#', 'hashtag');
    var tts_url = 'https://hosted.stylerdev.io/api/synthesize?voice=' + voice + '&text=' + encodeURI(message) + '&token=' + tts_authorization;
    //var tts_url = 'https://pajlada.se/files/clr/slap.mp3';
    //var tts_url = 'https://pajlada.se/files/fuckyou.mp3';

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
