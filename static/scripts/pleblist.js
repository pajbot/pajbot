var tag = document.createElement('script');
tag.src = 'https://www.youtube.com/iframe_api';
var firstScriptTag = document.getElementsByTagName('script')[0];
firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

var player;
var player_ready = false;
var current_song = null;
function onYouTubeIframeAPIReady()
{
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
    if (current_song !== null) {
        var song_just_played = pleblist_songs.shift();
        $('#song-'+song_just_played.id).remove();
        $.api({
            action: 'pleblist_next_song',
            method: 'post',
            on: 'now',
            beforeSend: function(settings) {
                settings.data.song_id = current_song.id;
                settings.data.password = secret_password;
                return settings;
            }
        });
        current_song = null;
    }

    if (pleblist_songs.length > 0) {
        current_song = pleblist_songs[0];
        player.loadVideoById({
            'videoId': current_song.youtube_id,
        });
    } else {
        player.stopVideo();
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
var pleblist_started = false;

function start_pleblist()
{
    pleblist_started = true;
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
    var title = '???';
    var song_length = '???';
    if (song.info !== null) {
        title = song.info.title;
        song_length = moment.duration(song.info.duration, 'seconds').format('h:mm:ss');
    }
    $a_header = $('<a>', {class: 'header', 'href': 'https://youtu.be/' + song.youtube_id, }).text(title);
    $div_content.append($a_header);
    $div_description = $('<div>', {class: 'description'}).text(song_length);
    $div_content.append($div_description);

    if (current_song == null && pleblist_started === true) {
        next_song();
    }
}

function update_song_counter()
{
    $('#num_songs').text(pleblist_songs.length);
    var total_duration = 0;
    for (song_id in pleblist_songs) {
        var song = pleblist_songs[song_id];
        if (song.info !== null) {
            total_duration += song.info.duration;
        }
    }
    $('#total_duration').text(moment.duration(total_duration, 'seconds').format('h:mm:ss'));
}

function process_songs(song_list)
{
    for (index in song_list) {
        var song = song_list[index];
        add_to_pleblist(song);
    }

    update_song_counter();
    if (pleblist_songs.length == 0) {
        //$('#start_button').show();
    }
}

secret_password = undefined;

$(document).ready(function() {
    secret_password = $.cookie('password');
    if (secret_password === undefined) {
        $('#message').html('Currently in Guest mode. Skip will not work.<br />Refresh this page after logging into the Host page. OMGScoots');
        setTimeout(function() {
            $.ajax({
                dataType: 'json',
                'url': '/api/v1/pleblist/list',
                success: function(response) {
                    process_songs(response.songs);
                },
                error: function(response) {
                }
            });
        }, 500);
    } else {
        $('#message').text('Currently in Client mode. Everything should work Kappa');
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
    }

    $('#skip_btn').click(function() {
        next_song();
    });

    $('#add_song').api({
        action: 'pleblist_add_song',
        method: 'post',
        data: {
            'password': secret_password
        },
        beforeSend: function(settings) {
            settings.data.password = secret_password;
            var youtube_id = parse_youtube_id_from_url($('#song_input').val());
            if (youtube_id === false) {
                return false;
            }
            settings.data.youtube_id = youtube_id;
            //$('#song_input').val('');
            return settings;
        }
    }).state({
        onActivate: function() {
            $(this).state('flash text');
        },
        text: {
            flash: 'Song added!',
        }
    });

    $('#add_song').click(function() {
        var song_url = $('#song_input').val();
        if (song_url.length > 0) {
            $('#song_input').val('');
        }
    })
});

