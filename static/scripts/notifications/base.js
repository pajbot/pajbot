function add_notification(message)
{
    var $notif = $('<div>', {class: 'item'}).text(message);
    $('.notifications.list').prepend($notif);

    /* TODO: play some DING sound */

    /* TODO: add some cool effect to make it more visible */
    notification_sound.play();
}

notification_sound = null;

$(document).ready(function() {
    connect_to_ws();
    //notification_sound = new Audio('https://pajlada.se/files/clr/psst.mp3');
    //notification_sound = new Audio('https://pajlada.se/files/clr/notificationpaj.wav');
    notification_sound = new Audio('https://pajlada.se/files/clr/suction.mp3');
    notification_sound.load();

    setTimeout(function() {
        add_notification('Karl_Kons just timed out NIGHTNACHT for 5000 points.');
    }, 1000);
});

isopen = false;

function connect_to_ws()
{
    if (isopen) {
        return;
    }
    console.log('Connecting to websocket....');
    socket = new WebSocket(ws_host);
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
                    case 'notify':
                        var message = json_data.data.user + ' used the !' + json_data.data.trigger + ' command! Arguments: ' + json_data.data.message;
                        add_notification(message);
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
