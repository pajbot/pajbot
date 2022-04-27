if (!String.prototype.format) {
    String.prototype.format = function() {
        var args = arguments;
        return this.replace(/{(\d+)}/g, function(match, number) {
            return typeof args[number] != 'undefined' ? args[number] : match;
        });
    };
}

$(document).ready(function() {
    connect_to_ws();
});

function add_random_box({ color }) {
    var divsize = 50;
    var posx = (Math.random() * ($(document).width() - divsize)).toFixed();
    var posy = (Math.random() * ($(document).height() - divsize)).toFixed();
    var $newdiv = $("<div class='exploding'></div>").css({
        left: `${posx}px`,
        top: `${posy}px`,
        'background-color': color,
        opacity: 0,
    });
    $newdiv.appendTo('body');
    $newdiv.animate(
        {
            opacity: 1,
        },
        500
    );
    setTimeout(function() {
        $newdiv.animate(
            {
                opacity: 0,
            },
            1000
        );
        setTimeout(function() {
            $newdiv.remove();
        }, 1000);
    }, 5000);
}

async function getEmoteURL({ urls }) {
    return new Promise((resolve, reject) => {
        let sortedSizes = Object.keys(urls)
            .map(size => parseInt(size))
            .sort();
        let largestSize = sortedSizes[sortedSizes.length - 1];
        let img = new Image();
        img.onload = () =>
            resolve({
                url: urls[String(largestSize)],
                needsScale: 4 / largestSize,
                img: img,
            });
        img.onerror = () => reject();
        img.src = urls[String(largestSize)];
    });
}

// opacity = number between 0 and 100
async function add_emotes({
    emotes,
    opacity,
    persistence_time: persistenceTime,
    scale: emoteScale,
}) {
    for (let emote of emotes) {
        // largest URL available
        let { url, needsScale, img } = await getEmoteURL(emote);

        let posX = `${Math.random() * 100}%`;
        let posY = `${Math.random() * 100}%`;

        let imgElement = $('<img class="absemote">')
            .css({
                transform: `scale(${(emoteScale / 100) * needsScale})`,
                'image-rendering': img.height < 100 ? 'pixelated' : 'auto',
            })
            .attr({ src: url });

        let containerDiv = $('<div class="absemote_container"></div>')
            .css({
                left: posX,
                top: posY,
                opacity: 0,
            })
            .append(imgElement)
            .appendTo('body');

        containerDiv.animate(
            {
                opacity: opacity / 100,
            },
            500
        );
        setTimeout(() => {
            containerDiv.animate(
                {
                    opacity: 0,
                },
                1000
            );
            setTimeout(() => {
                containerDiv.remove();
            }, 1000);
        }, persistenceTime);
    }
}

function show_custom_image(data) {
    var url = data.url;
    var divsize = 120;
    var posx = (Math.random() * ($(document).width() - divsize)).toFixed();
    var posy = (Math.random() * ($(document).height() - divsize)).toFixed();
    var css_data = {
        left: `${posx}px`,
        top: `${posy}px`,
        opacity: 0,
    };
    if (data.width !== undefined) {
        css_data.width = data.width;
    }
    if (data.height !== undefined) {
        css_data.height = data.height;
    }
    if (data.x !== undefined) {
        css_data.left = `${data.x}px`;
    }
    if (data.y !== undefined) {
        css_data.top = `${data.y}px`;
    }
    var $newdiv = $(`<img class="absemote" src="${url}">`).css(css_data);
    $newdiv.appendTo('body');
    $newdiv.animate(
        {
            opacity: 1,
        },
        500
    );
    setTimeout(function() {
        $newdiv.animate(
            {
                opacity: 0,
            },
            1000
        );
        setTimeout(function() {
            $newdiv.remove();
        }, 1000);
    }, 5000);
}

var message_id = 0;

function add_notification({ message }) {
    var new_notification = $(`<div>${message}</div>`).prependTo(
        'div.notifications'
    );
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
            new_notification.animate(
                {
                    height: 0,
                    opacity: 0,
                },
                1000
            );
        }, 2000);
    });
    new_notification.on('outAnimationEnd.tlt', function() {
        setTimeout(function() {
            new_notification.remove();
        }, 250);
    });
}

function refresh_combo_count(count) {
    $('#emote_combo span.count').html(count);
    $('#emote_combo span.count').addClass('animated pulsebig');
    $('#emote_combo span.count').on(
        'webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend',
        function() {
            $(this).removeClass('animated pulsebig');
        }
    );
    $('#emote_combo img').addClass('animated pulsebig');
    $('#emote_combo img').on(
        'webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend',
        function() {
            $(this).removeClass('animated pulsebig');
        }
    );
}

// https://gist.github.com/mkornblum/1384495
// slightly altered
$.fn.detachThenReattach = function(fn) {
    return this.each(function() {
        let $this = $(this);
        let tmpElement = $('<div style="display: none"/>');
        $this.after(tmpElement);
        $this.detach();
        fn.call($this);
        tmpElement.replaceWith($this);
    });
};

async function refresh_combo_emote(emote) {
    let { url, needsScale, img } = await getEmoteURL(emote);
    let $emoteCombo = $('#emote_combo img');

    // Fix for issue #378
    // we detach the <img> element from the DOM, then edit src and zoom,
    // then it is reattached where it used to be. This prevents the GIF animation
    // from resetting on all other emotes with the same URL on the screen
    $emoteCombo.detachThenReattach(function() {
        this.attr('src', url);
        this.css({
            zoom: String(needsScale),
            'image-rendering': img.height < 100 ? 'pixelated' : 'auto',
        });
    });
}

function debug_text(text) {
    //add_notification(text);
}

let current_emote_code = null;
let close_down_combo = null;

function refresh_emote_combo({ emote, count }) {
    let emote_combo = $('#emote_combo');
    if (emote_combo.length === 0) {
        current_emote_code = emote.code;
        let message = `x<span class="count">${count}</span> <img class="comboemote" /> combo!`;
        let new_notification = $(
            `<div id="emote_combo">${message}</div>`
        ).prependTo('div.notifications');
        new_notification.addClass('animated bounceInLeft');

        new_notification.on(
            'webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend',
            function() {
                if (new_notification.hasClass('ended')) {
                    new_notification.animate(
                        {
                            height: 0,
                            opacity: 0,
                        },
                        500
                    );
                    setTimeout(function() {
                        new_notification.remove();
                    }, 500);
                }
            }
        );

        clearTimeout(close_down_combo);
        close_down_combo = setTimeout(function() {
            new_notification.addClass('animated bounceOutLeft ended');
        }, 4000);
    } else {
        clearTimeout(close_down_combo);
        close_down_combo = setTimeout(function() {
            emote_combo.addClass('animated bounceOutLeft ended');
        }, 3000);
    }

    refresh_combo_emote(emote);
    refresh_combo_count(count);
}

function create_object_for_win(points) {
    return {
        value: points,
        color: '#64DD17',
    };
}

function create_object_for_loss(points) {
    return {
        value: points,
        color: '#D50000',
    };
}

function play_sound({ link, volume }) {
    let player = new Howl({
        src: [link],
        volume: volume * 0.01, // the given volume is between 0 and 100
        onend: () => console.log('Playsound audio finished playing'),
        onloaderror: e => console.warn('audio load error', e),
        onplayerror: e => console.warn('audio play error', e),
    });

    player.play();
}

function handleWebsocketData(json_data) {
    if (json_data['event'] === undefined) {
        return;
    }

    let data = json_data.data;
    switch (json_data['event']) {
        case 'new_box':
            add_random_box(data);
            break;
        case 'new_emotes':
            add_emotes(data);
            break;
        case 'notification':
            add_notification(data);
            break;
        case 'timeout':
            add_notification({
                message:
                    '<span class="user">' +
                    data.user +
                    '</span> timed out <span class="victim">' +
                    data.victim +
                    '</span> EleGiggle',
            });
            setTimeout(function() {
                // TODO idk kev maybe this will just stay removed with new playsounds system
                //play_sound('slap');
            }, 100);
            break;
        case 'play_sound':
            play_sound(data);
            break;
        case 'emote_combo':
            refresh_emote_combo(data);
            break;
        case 'show_custom_image':
            show_custom_image(data);
            break;
        case 'refresh':
        case 'reload':
            location.reload(true);
            break;
    }
}

let socket = null;

function connect_to_ws() {
    if (socket != null) {
        return;
    }

    console.log('Connecting to websocket....');
    socket = new WebSocket(ws_host);
    socket.binaryType = 'arraybuffer';
    socket.onopen = function() {
        console.log('WebSocket Connected!');
    };
    socket.onerror = function(event) {
        console.error('WebSocket error observed:', event);
    };
    socket.onmessage = function(e) {
        if (typeof e.data != 'string') {
            return;
        }

        let json_data = JSON.parse(e.data);
        console.log('Received data:', json_data);
        handleWebsocketData(json_data);
    };
    socket.onclose = function(e) {
        console.log(
            `WebSocket closed ${e.wasClean ? '' : 'un'}cleanly with reason ${
                e.code
            }: ${e.reason}`
        );
        socket = null;
        setTimeout(connect_to_ws, 2500);
    };
}
