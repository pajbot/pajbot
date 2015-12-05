var tag = document.createElement('script');
tag.src = 'https://www.youtube.com/iframe_api';
var firstScriptTag = document.getElementsByTagName('script')[0];
firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

var player;
var player_ready = false;
var current_song = null;
function onYouTubeIframeAPIReady()
{
    console.log('ready sir');
    player = new YT.Player('player', {
        height: '390',
        width: '640',
        events: {
            'onReady': onPlayerReady,
            'onStateChange': onPlayerStateChange
        }
    });
}

function next_song()
{
    if (pleblist_songs.length == 0) {
        return false;
    }

    if (current_song !== null) {
        var song_just_played = pleblist_songs.shift();
        $('#song-'+song_just_played.id).remove();
        $.ajax({
            dataType: 'json',
            'url': '/api/v1/pleblist/next',
        });
        current_song = null;
    }

    if (pleblist_songs.length > 0) {
        current_song = pleblist_songs[0];
        player.loadVideoById({
            'videoId': current_song.youtube_id,
        });
    }

    update_song_counter();
}

function onPlayerReady(event)
{
    console.log('player ready');
}

function onPlayerStateChange(event)
{
    if (event.data == YT.PlayerState.ENDED) {
        next_song();
    }
}

var pleblist_songs = [];
var latest_song_id = -1;

function start_pleblist()
{
    console.log('asd');
    if (pleblist_songs.length > 0) {
        $('#start_button').hide();
        next_song();
    }
}

function start_getting_new_songs()
{
    setInterval(function() {
        $.ajax({
            dataType: 'json',
            'url': '/api/v1/pleblist/list/after/' + latest_song_id,
            success: function(response) {
                process_songs(response.songs);
            },
            error: function(response) {
                console.log(response);
            }
        });
    }, 5 * 1000);
}

function add_to_pleblist(song)
{
    pleblist_songs.push(song);
    latest_song_id = song.id;
    $div = $('<div>', {class: 'item', id: 'song-' + song.id});
    $('#pleblist div.ui.list').append($div);
    $div_content = $('<div>', {class: 'content'});
    $div.append($div_content);
    $a_header = $('<a>', {class: 'header', 'href': 'https://youtu.be/' + song.youtube_id, }).text('SONG ' + song.id);
    $div_content.append($a_header);
    $div_description = $('<div>', {class: 'description'}).text('Song length here');
    $div_content.append($div_description);
}

function update_song_counter()
{
    $('#num_songs').text(pleblist_songs.length);
}

function process_songs(song_list)
{
    for (index in song_list) {
        var song = song_list[index];
        add_to_pleblist(song);
    }

    update_song_counter();
    if (pleblist_songs.length == 0) {
        $('#start_button').show();
    }
}

$(document).ready(function() {
    secret_password = $.cookie('password');
    setTimeout(function() {
        $.ajax({
            dataType: 'json',
            'url': '/api/v1/pleblist/list',
            success: function(response) {
                process_songs(response.songs);
                start_getting_new_songs();
            },
            error: function(response) {
                start_getting_new_songs();
            }
        });
    }, 500);

    $('#skip_btn').api({
        action: 'pleblist_next_song',
        method: 'post',
        beforeSend: function(settings) {
            settings.data.song_id = current_song.id;
            settings.data.password = '???'; // XXX how do we get this
            return settings;
        }
    });
});

