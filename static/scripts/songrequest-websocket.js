let socket = null;
var open = false;
function connect_to_ws() {
    if (socket != null) {
        return;
    }

    console.log('Connecting to websocket....');
    socket = new WebSocket(ws_host);
    socket.binaryType = "arraybuffer";
    socket.onopen = function () {
        console.log('WebSocket Connected!');
        socket.send(JSON.stringify({'event' : 'AUTH', 'data':{'access_token': auth.split(';')[1].split('&')[0]}})); 
    };
    socket.onerror = function (event) {
        console.error("WebSocket error observed:", event);
    };
    socket.onmessage = function (e) {
        if (typeof e.data != "string") {
            return;
        }

        let json_data = JSON.parse(e.data);
        handleWebsocketData(json_data);
    };
    socket.onclose = function (e) {
        console.log(`WebSocket closed ${e.wasClean ? '' : 'un'}cleanly with reason ${e.code}: ${e.reason}`);
        failedAttempts++;
        socket = null;
        location.reload();
    }

}

function handleWebsocketData(json_data) {
    if (json_data['event'] === undefined) {
        return;
    }
    switch (json_data['event']) {
        case 'initialize':
            initialize(json_data['data']);
            break;
        case 'play':
            play(json_data['data']);
            break;
        case 'volume':
            volume_to(json_data['data']);
            break;
        case 'seek':
            seek_to(json_data['data']);
            break;
        case 'pause':
            pause();
            break;
        case 'resume':
            resume();
            break;
        case 'playlist':
            update_playlist(json_data['data']);
            break;
        case 'stop':
            stop();
            break;
        case 'history':
            update_history(json_data['data']);
            break;
    }  
    console.log(json_data);
}
  
$( document ).ready(function() {
    connect_to_ws()
});


var player;
var temp_volume;
var seek;
var current_song_time = 0;
var actual_volume = 0
var paused = false
$(document).mouseup(function(e){
    if (temp_volume != player.volume) {
        $('.plyr__volume').find('input')[0].style.cssText = "--value:"+(player.volume*100)+"%"
        $('.plyr__volume').find('input')[0].value = player.volume
        console.log(JSON.stringify({'event' : 'VOLUME', 'data' : {'volume' : temp_volume}}))
        socket.send(JSON.stringify({'event' : 'VOLUME', 'data' : {'volume' : temp_volume}}))
    }
    if (seek != -1) {
        console.log(seek/100 * player.media.duration)
        $('.plyr__progress').find('input')[0].value = (player.currentTime/player.media.duration)*100
        $('.plyr__progress').find('input')[0].style.cssText = "--value:"+((player.currentTime/player.media.duration)*100)+"%"
        socket.send(JSON.stringify({'event' : 'SEEK', 'data' : {'seek_time' : seek/100 * player.media.duration}}))
        seek = -1
    }
});

jQuery(function ($) {
    'use strict'
    var supportsAudio = !!document.createElement('audio').canPlayType;
    if (supportsAudio) {
        // initialize plyr
        player = new Plyr('#audio1', {
            controls: [
                'restart',
                'play',
                'progress',
                'current-time',
                'duration',
                'volume'
            ],
            listeners: {
                play: function (e) {
                    // Your code here
                    if (paused) {
                        socket.send(JSON.stringify({'event' : 'RESUME', 'data' : {}}))
                    } else {
                        socket.send(JSON.stringify({'event' : 'PAUSE', 'data' : {}}))
                    }
                    //
                    return false;    // required on v3
                },
                seek: function (e) {
                    e.preventDefault();
                    seek = e.srcElement.value;
                    return false;
                },
                volume: function (e) {
                    e.preventDefault(); 
                    temp_volume = e.target.value
                    return false;
                }, 
                restart: function (e) {
                    socket.send(JSON.stringify({'event' : 'SEEK', 'data' : {'seek_time' : 0}}))
                    return false;    // required on v3
                }           
            }
        });
        player.on('ready', event => {
            seek = -1;
            player.play();
            if (player.currentTime != current_song_time) {
                player.currentTime = current_song_time;
                if (!paused) {
                    player.play()
                } else {
                    player.pause()
                }
            } else {
                player.pause()
                player.currentTime = 0
            }
            
            player.volume = actual_volume;
            temp_volume = actual_volume;
            sleep(1000).then(() => {
                player.embed.mute()
            });
        });
        $('#btnPrev').on('click', function () {
            socket.send(JSON.stringify({'event' : 'PREVIOUS', 'data' : {}}))
        });
        $('#btnNext').on('click', function () {
            socket.send(JSON.stringify({'event' : 'SKIP', 'data' : {}}))
        });

    } else {
        $('.column').addClass('hidden');
        var noSupport = $('#audio1').text();
        $('.container').append('<p class="no-support">' + noSupport + '</p>');
    }
});

function sleep (time) {
    return new Promise((resolve) => setTimeout(resolve, time));
}

function initialize(data) {
    update_playlist({'playlist' : data['playlist']})
    update_history({'history' : data['history']})
    if (data.currentSong != null) {
        play({'video_id' : data['currentSong']['video_id'], 'video_title' : data['currentSong']['video_title'], 'requested_by' : data['currentSong']['requested_by']})         
        current_song_time = data['currentSong']['current_song_time'] + 2.5
    } else {
        play({'video_id' : ''})
    } 
    try {
        player.embed.mute()
    } catch {
    }
    paused = data['paused'];
    actual_volume = data['volume']/100;
    temp_volume = data['volume']/100;
    open = data['open'];
    update_state();
}

function update_state() {
    if (open) {

    } else {

    }
}

function seek_to(data) {
    current_song_time = data['seek_time'];
    player.currentTime = current_song_time;
    pause()
    sleep(1000).then(() => {
        player.embed.mute()
    });
    
}

function pause() {
    player.pause()
    paused = true
    player.embed.mute()
}

function resume() {
    player.play()
    paused = false
    player.embed.mute()
}

function volume_to(data) {
    actual_volume = data['volume']/100;
    temp_volume = data['volume']/100;
    player.volume = actual_volume;
}

function play({video_id, video_title, requested_by}) {
    current_song_time = 0
    player.source = {
        type: 'video',
        sources: [
            {
                src: video_id,
                provider: 'youtube',
            },
        ],
    };
    if (video_id != "") {
        if (requested_by == null) {
            requested_by = "Backup Playlist"
        }
        $('#npAction').text(video_title + " ~ " + requested_by);
    } else {
        $('#npAction').text("No songs are currently playing");
    }
    try {
        player.embed.mute()
    } catch {
        
    }
}

var tracks;
function update_playlist({playlist}) {
    tracks = playlist;
    $("#plList tr").remove()
    for (var i = 0; i < playlist.length; i++) {
        item = playlist[i];
        var trackNumber = i+1,
            video_title = item.video_title,
            video_length = item.video_length,
            video_length = Math.floor(video_length / 60).toString() + ":" + (video_length - Math.floor(video_length / 60)*60).toString().padStart(2, '0');
            requested_by = item.requested_by;
            if (requested_by == null) {
                requested_by = "Backup Playlist"
            }

        if (trackNumber.toString().length === 1) {
            trackNumber = '0' + trackNumber;
        }
        $('#plList').append('\
            <tr class="plItem"> \
                <td class="plNum">' + trackNumber + '.</td> \
                <td class="plTitle">' + video_title + ' ~ ' + requested_by + '</td> \
                <td class="plLength">' + video_length + '</td> \
                <td class="plRemove"><img onmouseover="hover(this);" onmouseout="unhover(this);" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAABmJLR0QA/wD/AP+gvaeTAAAArklEQVRIie2Vuw2EMBBEkaA9CEkQtZgu3MARXYln6RHgwEK3ttefjIl3eMwY1sPwqkbABBzArPQtgAGm1OAInNxywJ4JWIGf932jIP8moRywJQCbnwtlYob5j0EECQCXrPoRPTTuJXPFoGpARhVWU2lpoqf0CZSgekAAsgLEtgL0TdL9TOj9dQkJ2v0nuQ8oBnGv6xa7a4lBjLZrARTdwiPw0XaM5j7xhr4346uULs6HIhGcHYNqAAAAAElFTkSuQmCC"></td> \
            </tr>\
            ');
    }
    
    $('.plRemove').click(function (event) {
        var id = parseInt($('#plList tr').index($(this).closest("tr")));
        socket.send(JSON.stringify({'event' : 'REMOVE', 'data' : {'database_id' : tracks[id].database_id}}))
    });
    $('#plList tr td').click(function (event) {
        if (!$(this).hasClass('plRemove')) {
            var id = parseInt($('#plList tr').index($(this).closest("tr")));
            console.log({'event' : 'PLAY', 'data' : {'database_id' : tracks[id].database_id}})
            socket.send(JSON.stringify({'event' : 'PLAY', 'data' : {'database_id' : tracks[id].database_id}}))
        }
    });
}
var hist_tracks;
function update_history({history}) {
    hist_tracks = history;
    $("#buList tr").remove()
    for (var i = 0; i < history.length; i++) {
        item = history[i];
        var trackNumber = i+1,
            video_title = item.video_title,
            video_length = item.video_length,
            video_length = Math.floor(video_length / 60).toString() + ":" + (video_length - Math.floor(video_length / 60)*60).toString().padStart(2, '0');
            requested_by = item.requested_by;
            if (requested_by == null) {
                requested_by = "Backup Playlist"
            }
        if (trackNumber.toString().length === 1) {
            trackNumber = '0' + trackNumber;
        }
        $('#buList').append('\
            <tr class="buItem"> \
                <td class="buNum">' + trackNumber + '.</td> \
                <td class="buTitle">' + video_title + ' ~ ' + requested_by + '</td> \
                <td class="buLength">' + video_length + '</td> \
                <td class="buRequeue"><img onmouseover="hover_requeue(this);" onmouseout="unhover_requeue(this);" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAABmJLR0QA/wD/AP+gvaeTAAABjklEQVRIid2UvU4CQRDHZ+21QK5R/OjVQmmBSm3V0s4HkGh8Ap6B4HNI7KTy4wFMBDsLA7FSqWig+VncbFwuu3CXq3SSyyR7/5nfzt3MiPw7Ay6AYeA5dXRXwAtwC9SBtaygBn47m6GZANdAlBfkQlaAfeASuHc0A6CcFrILjEMQj74C9FQ3mgsCIqCvAW9pIBq3CNw5FYU/HdBSYVcDG2kgDshW1AqJSvoTASrOeSMNRLVVpxlKPkFdBQ+ed4U0ENU+ap5ze7bgvD9Uf5MMNMYM00KceJtvCrKhvpshoc966td9EPtJstzaZ1/qiz7It/rlnBDbvp8+SF/9dk7IViLfFKSj/jgn5CSR79dCc5LFgJrGj4HVkOjanfiMgCXgVeObs4SR7h50F6UC6UrpaFwfKM4LKOs2RXdRdY6+5lQwAvaSGhMCiUhbROz+eZJ4knsSz1FBRHYkbhJ7iYGIHBljnmdWkQBFupVtM4RsAjSB4Hx5K0nASnrjAxHZ1CqGIvIucZu2jTEfqW//p+0HEVIh1z1nYUsAAAAASUVORK5CYII="></td> \
            </tr>\
            ');
    }
    
    $('.buRequeue').click(function (event) {
        var id = parseInt($('#buList tr').index($(this).closest("tr")));
        console.log({'event' : 'REQUEUE', 'data' : {'database_id' : hist_tracks[id].database_id}})
        socket.send(JSON.stringify({'event' : 'REQUEUE', 'data' : {'database_id' : hist_tracks[id].database_id}}))
    });
}

function hover(element) {
    element.setAttribute('src', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAABmJLR0QA/wD/AP+gvaeTAAABjElEQVRIie2VsU7CUBSGvwNdTHyAwlsw14FdcDBCIsQQBgefQUZ5BxNMFAkOhjjYupMIoz4G5QFIWCDXgdbclt5SFibOeHrzf/ecc/9TOMYeIfGEKpet+emqI/BjexM3q9D83LlQIiV7YXVlPF4ZIapWy/tL/1WgAayV0C66k8EugF916igZAhYwshfWtQ7KRW6z9DsBACAviudZxWmmAWYVp4mStwAAcDU/Xd3rZyIQgV9graXygvRNoFnFaQrSB/Jaeh3oJENsb+IiqgHoPd2Aqmc3+lm/6tQFeYkDlNCOz3Jr8KGA1uOIQNGdDHZ9j+slQsDcCpAeqNutClCtojcdJmkZISkVxWPnK0yFZABleua5tI8ABXf6DvJkuGMvi48OUslBZmJsV4KTYfO6HokbdsdmSISkGa3gfd9lNWwYW+3KarR9DBmBBOv6Y6sCg9GMu0upS/tr+hkmIu1SIqWsAICiNx0qVIvYjAKd/4guyJPCgyCh4KZ0A0AHxWY0shdWVz9zkD/jMfaKP4e24tauhPoQAAAAAElFTkSuQmCC');
}

function unhover(element) {
    element.setAttribute('src', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAABmJLR0QA/wD/AP+gvaeTAAAArklEQVRIie2Vuw2EMBBEkaA9CEkQtZgu3MARXYln6RHgwEK3ttefjIl3eMwY1sPwqkbABBzArPQtgAGm1OAInNxywJ4JWIGf932jIP8moRywJQCbnwtlYob5j0EECQCXrPoRPTTuJXPFoGpARhVWU2lpoqf0CZSgekAAsgLEtgL0TdL9TOj9dQkJ2v0nuQ8oBnGv6xa7a4lBjLZrARTdwiPw0XaM5j7xhr4346uULs6HIhGcHYNqAAAAAElFTkSuQmCC');
}
function hover_requeue(element) {
    element.setAttribute('src', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAABmJLR0QA/wD/AP+gvaeTAAACtUlEQVRIid2UTUtUYRTHf+e5M7WIgixBp7Fapy7ERYTXyY3C+NYEfYDaCNUi6guofYOEyGrTro3gNDMR2cacK0pQLbJlEDmNgS8bcZHe+5wW49A0d9Ipd/7hwsPznHN+5+Vy4LBIyocfg+4dhdGaRsLtpqz3HKA46N4T4TrKV1F5E0QkfebF3PJeEFM+NOW8B8AEcLL6U+RoRVYnUNqBIRWdMNZ+WRlwH64kuxv3hQA057wxYHyvrCJGnxilV1XvAm9Rogi3cPRDccDtrNmJ6ovvw4kOY+0icOS3ldxozuaf1QpQHHJdUSaBVmBLlcuxl977v1aykuxuNNa+AI4gfNmrorJiWc+LGL0kyAxwTIR0dev+gODoKNACLEVEO9indWU1ZuY3HWOvAZ+B+G6cMKSQ7IkjjACocLMxM79Zz4wqQap6EwBhpJDsiYcgERNcLQ1R52JZzyvfN+e8MX/bz9QDir2czwN5lKjj7KRCEBXtA1DLdLVzy+uFjXogpTiy6y99IQjCOQAj5lO9AWvJEbsEoHA2BBGlASAwUnfWteTjrO0GPh2CKKwDRAJ76iAQUb/8+66GIMA3gABtOwgEnFYARb6FIKIyAyAiqbBj/RLVq6WTzoQgvnWmEXaAy8Uh1/0fQLE/kQC6gW2fIB2CxF/NFrA8LWXDo9XhruP/AlhPXjwhYh/tlvO4JbfwPQQBwMoYUADaAmum6gWtDncd/2miUwgXgGUler/y/c9V/yq/qkoK2FK0z7eyUBzo6t4LUOxPJPxAFkXoBbZUJBXLzq5V2oRWPUBxwO0UIQ2U909eRaYdsUtBIBuOow2BlXaBFKUZACxbY66cycx9rI5XEwKltY+jowgjKNG/liLsgE4GkZ3x+PS79dom+6iQ7ImXlp3pBT0PNAAbIF9BZ3yCdOWQD7d+AS3iAH0Q75jOAAAAAElFTkSuQmCC');
}

function unhover_requeue(element) {
    element.setAttribute('src', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAABmJLR0QA/wD/AP+gvaeTAAABjklEQVRIid2UvU4CQRDHZ+21QK5R/OjVQmmBSm3V0s4HkGh8Ap6B4HNI7KTy4wFMBDsLA7FSqWig+VncbFwuu3CXq3SSyyR7/5nfzt3MiPw7Ay6AYeA5dXRXwAtwC9SBtaygBn47m6GZANdAlBfkQlaAfeASuHc0A6CcFrILjEMQj74C9FQ3mgsCIqCvAW9pIBq3CNw5FYU/HdBSYVcDG2kgDshW1AqJSvoTASrOeSMNRLVVpxlKPkFdBQ+ed4U0ENU+ap5ze7bgvD9Uf5MMNMYM00KceJtvCrKhvpshoc966td9EPtJstzaZ1/qiz7It/rlnBDbvp8+SF/9dk7IViLfFKSj/jgn5CSR79dCc5LFgJrGj4HVkOjanfiMgCXgVeObs4SR7h50F6UC6UrpaFwfKM4LKOs2RXdRdY6+5lQwAvaSGhMCiUhbROz+eZJ4knsSz1FBRHYkbhJ7iYGIHBljnmdWkQBFupVtM4RsAjSB4Hx5K0nASnrjAxHZ1CqGIvIucZu2jTEfqW//p+0HEVIh1z1nYUsAAAAASUVORK5CYII=');
}

$(function() {
    $( "#plList" ).sortable({
      placeholder: "sortable-placeholder",
      items: 'tr',
      helper: function(e, tr)
      {
        var $originals = tr.children();
        var $helper = tr.clone();
        $helper.children().each(function(index)
        {
        // Set helper cell sizes to match the original sizes
        $(this).width($originals.eq(index).width());
        });
        return $helper;
      },
      start: function (evt, ui) {
        sourceIndex = $(ui.item).index()-1;
      },
      stop: function(evt, ui) { 
        console.log({'event' : 'MOVE', 'data' : {'database_id' : tracks[sourceIndex].database_id, 'to_id' : ui.item.index()}})
        socket.send(JSON.stringify({'event' : 'MOVE', 'data' : {'database_id' : tracks[sourceIndex].database_id, 'to_id' : ui.item.index()}}))
        $(this).sortable('cancel');
      }
    })
});

function stop() {
    player.stop()
    play({video_id : ''})
}