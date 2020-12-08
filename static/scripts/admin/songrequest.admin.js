var player;
var open = false;
var done = false;
var socket = null;
var enabled = false;
var requests_open = false;
var auto_play = false;
var backup_playlist = false;
var paused = false;
var use_spotify = false;
var show_video = false;
var currentqueuebody = $('#currentqueuebody');
var currentsong = null;
var playerstate = true;
var play_on_stream = false;

$('main.main.container')
    .find('div.ui.container')
    .removeClass('container');

function connect_to_ws() {
    if (socket != null) {
        return;
    }

    console.log('Connecting to websocket....');
    socket = new WebSocket(ws_host);
    socket.binaryType = 'arraybuffer';
    socket.onopen = () => {
        console.log('WebSocket Connected!');
        socket.send(
            JSON.stringify({
                event: 'AUTH',
                data: { access_token: auth },
            })
        );
    };
    socket.onerror = event => {
        console.error('WebSocket error observed:', event);
    };
    socket.onmessage = e => {
        if (typeof e.data != 'string') {
            return;
        }

        let json_data = JSON.parse(e.data);
        handleWebsocketData(json_data);
    };
    socket.onclose = e => {
        console.log(
            `WebSocket closed ${e.wasClean ? '' : 'un'}cleanly with reason ${
                e.code
            }: ${e.reason}`
        );
        socket = null;
        connect_to_ws();
    };
}

function handleWebsocketData(json_data) {
    if (json_data['event'] === undefined) {
        return;
    }
    console.log(json_data);
    var start = new Date().getTime();
    switch (json_data['event']) {
        case 'initialize':
            initialize_player(json_data['data']);
            break;
        case 'play':
            current_song(json_data['data']);
            break;
        case 'volume':
            set_volume(json_data['data']);
            break;
        case 'playlist':
            set_playlist(json_data['data']);
            break;
        case 'backup_playlist':
            set_backup_playlist(json_data['data']);
            break;
        case 'history_list':
            set_history_list(json_data['data']);
            break;
        case 'favourite_list':
            set_favourite_list(json_data['data']);
            break;
        case 'banned_list':
            set_banned_list(json_data['data']);
            break;
        case 'module_state':
            set_module_state(json_data['data']);
            break;
        case 'update_current_song':
            current_song(json_data['data'], false);
            break;
        case 'alert_message':
            alert_message(json_data['data']);
            break;
    }
    console.log(new Date().getTime() - start);
}

function initialize_player(data) {
    // volume
    set_volume(data);
    // module_state
    set_module_state(data);
    // current_song
    current_song(data);
    // playlist
    set_playlist(data);
    // backup_playlist
    set_backup_playlist(data);
    // history_list
    set_history_list(data);
    // favourite_list
    set_favourite_list(data);
    // banned_list
    set_banned_list(data);
}

function onYouTubeIframeAPIReady() {
    player = new YT.Player('video_player', {
        playerVars: { autoplay: 0, controls: 0, mute: 1 },
        videoId: '',
        events: {
            onReady: onPlayerReady,
            onStateChange: onPlayerStateChange,
        },
    });
}
var first_run = true;
function onPlayerReady(event) {
    if (first_run) {
        first_run = false;
        connect_to_ws();
    }
    player.playVideo();
}

function timer() {
    var playerTotalTime = player.getDuration();
    if (playerTotalTime == 0) {
        playerTotalTime++;
    }
    var playerCurrentTime = player.getCurrentTime();
    var playerTimeDifference = (playerCurrentTime / playerTotalTime) * 100;
    var minutes = Math.floor(playerCurrentTime / 60);
    var seconds = Math.floor(playerCurrentTime - minutes * 60);
    $('#videotime').progress('set percent', playerTimeDifference);
    $('#videocurrenttime').text(minutes + ':' + ('0' + seconds).slice(-2));
    if (player.getVolume() != $('#volume').progress('get percent')) {
        player.setVolume($('#volume').progress('get percent'));
    }
}

function pause() {
    if (paused) {
        player.pauseVideo();
    }
    if (!play_on_stream) {
        player.unMute();
    }
    player.setVolume($('#volume').progress('get percent'));
}

function onPlayerStateChange(event) {
    if (paused) {
        setTimeout(pause, 1000);
        player.mute();
    }
    timer();
    if (event.data == YT.PlayerState.PLAYING) {
        mytimer = setInterval(timer, 300);
        if (!play_on_stream && !paused) {
            socket.send(
                JSON.stringify({
                    event: 'READY',
                })
            );
        }
    } else {
        if (event.data == YT.PlayerState.ENDED && !play_on_stream) {
            socket.send(
                JSON.stringify({
                    event: 'NEXT',
                })
            );
        }
        try {
            clearTimeout(mytimer);
        } catch {}
    }
}

function current_song(data, update = true) {
    if (Object.keys(data['current_song']).length === 0) {
        $('#status').text('No songs currently playing!');
        $('#songname').hide();
        $('#url').hide();
        if (update) {
            player.loadVideoById('');
            player.stopVideo();
        }
        $('#ban_current_video').addClass('disabled');
        $('#favourite_current_video').addClass('disabled');
        $('#favourite_current_video').html('Favourite Video');
        currentsong = null;
        $('#current_thumbnail').hide();
        $('#video_player').show();
    } else {
        if (update) {
            player.stopVideo();
        }
        $('#status').text(
            'Now Playing - ' + data['current_song']['requested_by']
        );
        $('#songname').show();
        $('#url').show();
        $('#song_title').text(data['current_song']['song_info']['title']);
        var url = $('#url a');
        url.text(
            'https://www.youtube.com/watch?v=' +
                data['current_song']['song_info']['video_id']
        );

        url.attr(
            'href',
            'https://www.youtube.com/watch?v=' +
                data['current_song']['song_info']['video_id']
        );

        url.attr('target', '_blank');

        if (update) {
            var time_diff =
                Math.floor(new Date().getTime() / 1000) -
                parseFloat(data['current_timestamp']) +
                0.5;
            var start_time = Math.round(
                data['current_song']['current_song_time'] + time_diff,
                2
            );
            console.log(start_time);
            player.loadVideoById({
                videoId: data['current_song']['song_info']['video_id'],
                startSeconds: start_time > 0 ? start_time : 0.01,
            });
        }
        $('#ban_current_video').removeClass('disabled');
        $('#favourite_current_video').removeClass('disabled');
        $('#favourite_current_video').html(
            data['current_song']['song_info']['favourite']
                ? 'Unfavourite Video'
                : 'Favourite Video'
        );
        $('#current_thumbnail').attr(
            'src',
            `https://img.youtube.com/vi/${data['current_song']['song_info']['video_id']}/maxresdefault.jpg`
        );
        if (playerstate) {
            $('#change_player_state').html('Enable Player');
            $('#current_thumbnail').show();
            $('#video_player').hide();
        } else {
            $('#change_player_state').html('Disable Player');
            $('#current_thumbnail').hide();
            $('#video_player').show();
        }
        currentsong = data['current_song'];
    }
}

$('#ban_current_video').on('click', e => {
    socket.send(
        JSON.stringify({
            event: 'BAN',
            data: {
                database_id: currentsong.database_id,
            },
        })
    );
});

$('#favourite_current_video').on('click', e => {
    socket.send(
        JSON.stringify({
            event: currentsong.song_info.favourite
                ? 'UNFAVOURITE'
                : 'FAVOURITE',
            data: {
                database_id: currentsong.database_id,
            },
        })
    );
});

$('#change_player_state').on('click', e => {
    if (playerstate) {
        $('#change_player_state').html('Disable Player');
        $('#current_thumbnail').hide();
        $('#video_player').show();
        playerstate = false;
    } else {
        $('#change_player_state').html('Enable Player');
        $('#current_thumbnail').show();
        $('#video_player').hide();
        playerstate = true;
    }
});

function set_volume(data) {
    player.setVolume(data['volume']);
    $('#volume').progress('set percent', data['volume']);
}

function set_playlist(data) {
    var table = $('#currentqueuebody');
    table.empty();
    data['playlist'].forEach(song => {
        table.append(`
        <tr data-id="${song.database_id}" data-banned="${
            song.song_info.banned
        }" data-favourite="${song.song_info.favourite}">
            <td class="center aligned"><i class="bars icon"></i></td>
            <td><p><a href="https://youtu.be/${
                song.song_info.video_id
            }" target="_blank">${song.song_info.title}</a></p><p>Requested by ${
            song.requested_by
        }</p></td>
            <td class="right aligned">
                <button class="circular ui icon basic button" onclick="favourite_control.call(this,event)"><i class="big heart${
                    song.song_info.favourite ? '' : ' outline'
                } icon"></i></button>
                <div class="ui dropdown">
                    <button class="circular ui icon basic button"><i class="big close icon"></i></button>
                    <div class="menu">
                        <div class="item" onclick="delete_control.call(this,event)">Delete Video</div>
                        <div class="item" onclick="ban_control.call(this,event)">${
                            song.song_info.banned ? 'Unban' : 'Ban'
                        } Video</div>
                    </div>
                </div>
            </td>
        </tr>
        `);
    });
    $('.ui.dropdown').dropdown();
}

function set_backup_playlist(data) {
    var table = $('#backupqueuebody');
    table.empty();
    data['backup_playlist'].forEach(song => {
        table.append(`
        <tr data-id="${song.database_id}" data-banned="${
            song.song_info.banned
        }" data-favourite="${song.song_info.favourite}">
            <td class="center aligned"><i class="bars icon"></i></td>
            <td><a href="https://youtu.be/${
                song.song_info.video_id
            }" target="_blank">${song.song_info.title}</a></td>
            <td class="right aligned">
                <button class="circular ui icon basic button" onclick="favourite_control.call(this,event)"><i class="big heart${
                    song.song_info.favourite ? '' : ' outline'
                } icon"></i></button>
                <div class="ui dropdown">
                    <button class="circular ui icon basic button"><i class="big close icon"></i></button>
                    <div class="menu">
                        <div class="item" onclick="delete_control.call(this,event)">Delete Video</div>
                        <div class="item" onclick="ban_control.call(this,event)">${
                            song.song_info.banned ? 'Unban' : 'Ban'
                        } Video</div>
                    </div>
                </div>
            </td>
        </tr>
        `);
    });
    $('.ui.dropdown').dropdown();
}

function set_history_list(data) {
    var table = $('#historybody');
    table.empty();
    var i = 1;
    data['history_list'].forEach(song => {
        table.append(`
        <tr data-histid="${song.database_id}" data-banned="${
            song.song_info.banned
        }" data-favourite="${song.song_info.favourite}">
            <td>${i}.</td>
            <td><p><a href="https://youtu.be/${
                song.song_info.video_id
            }" target="_blank">${song.song_info.title}</a></p><p>Requested by ${
            song.requested_by
        }</td>
            <td class="right aligned">
                <button class="circular ui icon basic button" onclick="favourite_control.call(this,event)"><i class="big heart${
                    song.song_info.favourite ? '' : ' outline'
                } icon"></i></button>
                <button class="circular ui icon basic button" onclick="replay_control.call(this,event)"><i class="big undo icon"></i></button>
                <div class="ui dropdown">
                    <button class="circular ui icon basic button"><i class="big close icon"></i></button>
                    <div class="menu">
                        <div class="item" onclick="ban_control.call(this,event)">${
                            song.song_info.banned ? 'Unban' : 'Ban'
                        } Video</div>
                    </div>
                </div>
            </td>
        </tr>
        `);
        i++;
    });
    $('.ui.dropdown').dropdown();
}

function set_favourite_list(data) {
    var table = $('#favouritelist');
    table.empty();
    var i = 1;
    data['favourite_list'].forEach(song_info => {
        table.append(`
        <tr data-infoid="${song_info.video_id}" data-banned="${
            song_info.banned
        }" data-favourite="${song_info.favourite}">
            <td>${i}.</td>
            <td><a href="https://youtu.be/${
                song_info.video_id
            }" target="_blank">${song_info.title}</a></td>
            <td class="right aligned">
                <button class="circular ui icon basic button" onclick="favourite_control.call(this,event)"><i class="big heart${
                    song_info.favourite ? '' : ' outline'
                } icon"></i></button>
                <button class="circular ui icon basic button" onclick="replay_control.call(this,event)"><i class="big undo icon"></i></button>
                <div class="ui dropdown">
                    <button class="circular ui icon basic button"><i class="big close icon"></i></button>
                    <div class="menu">
                        <div class="item" onclick="ban_control.call(this,event)">${
                            song_info.banned ? 'Unban' : 'Ban'
                        } Video</div>
                    </div>
                </div>
            </td>
        </tr>
        `);
        i++;
    });
    $('.ui.dropdown').dropdown();
}

function set_banned_list(data) {
    var table = $('#bannedlist');
    table.empty();
    var i = 1;
    data['banned_list'].forEach(song_info => {
        table.append(`
        <tr data-infoid="${song_info.video_id}" data-banned="${
            song_info.banned
        }" data-favourite="${song_info.favourite}">
            <td>${i}.</td>
            <td><a href="https://youtu.be/${
                song_info.video_id
            }" target="_blank">${song_info.title}</a></td>
            <td class="right aligned">
                <button class="circular ui icon basic button" onclick="favourite_control.call(this,event)"><i class="big heart${
                    song_info.favourite ? '' : ' outline'
                } icon"></i></button>
                <div class="ui dropdown">
                    <button class="circular ui icon basic button"><i class="big close icon"></i></button>
                    <div class="menu">
                        <div class="item" onclick="ban_control.call(this,event)">${
                            song_info.banned ? 'Unban' : 'Ban'
                        } Video</div>
                    </div>
                </div>
            </td>
        </tr>
        `);
        i++;
    });
    $('.ui.dropdown').dropdown();
}

function set_module_state(data) {
    enabled = data['module_state']['enabled'];
    requests_open = data['module_state']['requests_open'];
    auto_play = data['module_state']['auto_play'];
    backup_playlist = data['module_state']['backup_playlist'];
    paused = data['module_state']['paused'];
    use_spotify = data['module_state']['use_spotify'];
    show_video = data['module_state']['show_video'];
    play_on_stream = data['module_state']['play_on_stream'];

    $('#video_showing_state').html(show_video ? 'Hide Video' : 'Show Video');
    $('#requests_open_state').html(
        requests_open ? 'Disable Requests' : 'Enable Requests'
    );
    $('#auto_play_state').html(
        auto_play ? 'Disable Auto Play' : 'Enable Auto Play'
    );
    $('#backup_playlist_usage_state').html(
        backup_playlist ? 'Disable Backup Playlist' : 'Enable Backup Playlist'
    );
    $('#use_spotify_state').html(
        use_spotify ? 'Disable Spotify' : 'Enable Spotify'
    );
    $('#play_on_stream_state').html(
        play_on_stream ? 'Play in browser' : 'Play on stream'
    );
    $('#control_state').html(
        paused ? '<i class="play icon"></i>' : '<i class="pause icon"></i>'
    );

    if (player.getDuration() > 0) {
        if (paused) {
            player.pauseVideo();
        } else {
            player.playVideo();
        }
    }
    if (play_on_stream) {
        player.mute();
    } else {
        console.log($('#volume').progress('get percent'));
        player.setVolume($('#volume').progress('get percent'));
        player.unMute();
    }
    if (data['module_state']['backup_playlist_id']) {
        $('#backup_playlist_input').val(
            `https://www.youtube.com/playlist?list=${data['module_state']['backup_playlist_id']}`
        );
    }
}

function replay_control(event) {
    var tr = $(this).closest('tr');
    var button = $(this).closest('button');
    button.removeClass('icon');
    button.addClass('loading');
    button.addClass('tiny');
    socket.send(
        JSON.stringify({
            event: 'REQUEST',
            data: tr.data('infoid')
                ? { songinfo_database_id: tr.data('infoid') }
                : tr.data('histid')
                ? { hist_database_id: tr.data('histid') }
                : { database_id: tr.data('id') },
        })
    );
}

function favourite_control(event) {
    var tr = $(this).closest('tr');
    var button = $(this).closest('button');
    button.removeClass('icon');
    button.addClass('loading');
    button.addClass('tiny');
    socket.send(
        JSON.stringify({
            event: tr.data('favourite') ? 'UNFAVOURITE' : 'FAVOURITE',
            data: tr.data('infoid')
                ? { songinfo_database_id: tr.data('infoid') }
                : tr.data('histid')
                ? { hist_database_id: tr.data('histid') }
                : { database_id: tr.data('id') },
        })
    );
}

function ban_control(event) {
    var tr = $(this).closest('tr');
    var button = $(this).find('button');
    button.removeClass('icon');
    button.addClass('loading');
    button.addClass('tiny');
    socket.send(
        JSON.stringify({
            event: tr.data('banned') ? 'UNBAN' : 'BAN',
            data: tr.data('infoid')
                ? { songinfo_database_id: tr.data('infoid') }
                : tr.data('histid')
                ? { hist_database_id: tr.data('histid') }
                : { database_id: tr.data('id') },
        })
    );
}

function delete_control(event) {
    var tr = $(this).closest('tr');
    socket.send(
        JSON.stringify({
            event: 'DELETE',
            data: { database_id: tr.data('id') },
        })
    );
}

currentqueuebody
    .sortable({
        appendTo: 'parent',
        items: '> tr',
        helper: (e, tr) => {
            var $originals = tr.children();
            var $helper = tr.clone();
            $helper.children().each(index => {
                $(this).width($originals.eq(index).width());
            });
            return $helper;
        },
        start: (evt, ui) => {
            sourceIndex = $(ui.item).index();
        },
        stop: (evt, ui) => {
            if (sourceIndex === ui.item.index()) return;
            console.log(sourceIndex + ' to ' + ui.item.index());
            socket.send(
                JSON.stringify({
                    event: 'MOVE',
                    data: {
                        database_id: ui.item.data('id'),
                        to_id: ui.item.index() + 1,
                    },
                })
            );
            setTimeout(() => {
                currentqueuebody.sortable('cancel');
            }, 0);
        },
    })
    .disableSelection();

$('#control_state').on('click', function(e) {
    if (!paused) {
        socket.send(
            JSON.stringify({
                event: 'PAUSE',
            })
        );
    } else {
        socket.send(
            JSON.stringify({
                event: 'RESUME',
            })
        );
    }
});

$('#control_previous').on('click', function(e) {
    socket.send(
        JSON.stringify({
            event: 'PREVIOUS',
        })
    );
});

$('#control_next').on('click', function(e) {
    socket.send(
        JSON.stringify({
            event: 'NEXT',
        })
    );
});

$('#videotime').on('click', function(e) {
    socket.send(
        JSON.stringify({
            event: 'SEEK',
            data: {
                seek_time:
                    player.getDuration() *
                    ((e.pageX - $(this).offset().left) /
                        $('#videotime').width()),
            },
        })
    );
});

$('#volume').on('click', function(e) {
    socket.send(
        JSON.stringify({
            event: 'VOLUME',
            data: {
                volume: Math.round(
                    ((e.pageX - $(this).offset().left) / $('#volume').width()) *
                        100
                ),
            },
        })
    );
});

$('#requests_open_state').on('click', function(e) {
    socket.send(
        JSON.stringify({
            event: 'REQUEST_STATE',
            data: {
                value: !requests_open,
            },
        })
    );
});

$('#auto_play_state').on('click', function(e) {
    socket.send(
        JSON.stringify({
            event: 'AUTO_PLAY_STATE',
            data: {
                value: !auto_play,
            },
        })
    );
});

$('#backup_playlist_usage_state').on('click', function(e) {
    socket.send(
        JSON.stringify({
            event: 'BACKUP_PLAYLIST_STATE',
            data: {
                value: !backup_playlist,
            },
        })
    );
});

$('#use_spotify_state').on('click', function(e) {
    socket.send(
        JSON.stringify({
            event: 'USE_SPOTIFY_STATE',
            data: {
                value: !use_spotify,
            },
        })
    );
});

$('#play_on_stream_state').on('click', function(e) {
    socket.send(
        JSON.stringify({
            event: 'PLAY_ON_STREAM_STATE',
            data: {
                value: !play_on_stream,
            },
        })
    );
});

$('#video_showing_state').on('click', function(e) {
    socket.send(
        JSON.stringify({
            event: show_video ? 'HIDE_VIDEO' : 'SHOW_VIDEO',
        })
    );
});

let messageBox = $('#messages-box');

function alert_message(data) {
    // reset state...
    var message = $(`<div class="ui ${
        data.success ? 'success' : 'error'
    } message">
            <i class="close icon" onclick="$(this).remove()"></i>
            <div class="header">
            ${data.header}
            </div>
            <p>${data.text}</p>
        </div>`);
    message
        .appendTo(messageBox)
        .delay(data.duration)
        .queue(function() {
            $(this).remove();
        });
}

let add_media = $('#add-media-button');
$('#new-media-form').submit(function(event) {
    event.preventDefault();
    let formData = getFormData(event.target);
    console.log('New media');
    console.log(formData);
    add_media.text('Adding Media...');
    add_media.addClass('disabled');
    setTimeout(() => {
        add_media.text('Add Media');
        add_media.removeClass('disabled');
    }, 2000);
    socket.send(
        JSON.stringify({
            event: 'ADD_MEDIA',
            data: formData,
        })
    );
    $(this)
        .closest('form')
        .find('input[type=text], textarea')
        .val('');
});

$('#set-backup-playlist-form').submit(function(event) {
    event.preventDefault();
    let formData = getFormData(event.target);
    console.log('Set playlist');
    console.log(formData);
    add_media.text('Setting Playlist...');
    add_media.addClass('disabled');
    setTimeout(() => {
        add_media.text('Set Playlist');
        add_media.removeClass('disabled');
    }, 5000);
    socket.send(
        JSON.stringify({
            event: 'SET_BACKUP_PLAYLIST',
            data: formData,
        })
    );
});

$(document).ready(function() {
    var tag = document.createElement('script');

    tag.src = 'https://www.youtube.com/iframe_api';
    var firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

    $('#songname').hide();
    $('#url').hide();
    $('#current_thumbnail').hide();

    $('#volume').progress({
        autoSuccess: false,
        showActivity: false,
    });
    $('#videotime').progress({
        autoSuccess: false,
        showActivity: false,
    });
    $('.menu .item').tab();
});

function getFormData(form) {
    let data = $(form)
        .serializeArray()
        .reduce((obj, item) => {
            obj[item.name] = item.value;
            return obj;
        }, {});
    return data;
}
