function add_subs_notification(message)
{
    $('.content.subs').prepend('<div class="date" data-livestamp="' + moment.utc().format() + '"></div><div class="summary">' + message + '<hr style="visibility:hidden;" /></div>');
        $('.content.subs div:gt(7)').remove();
}

$(document).ready(function() {
    connect_to_ws();
    setTimeout(function() {
        add_subs_notification('~ Test subscriber ~');
    }, 2000);
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
            if (json_data['event'] !== undefined) {
                switch (json_data['event']) {
                    case 'new_sub':
                        var message = '<strong>' + json_data.data.username + '</strong> - new';
                        add_subs_notification(message);
                        break;
                    case 'resub':
                        var message = '<strong>' + json_data.data.username + '</strong> - <strong>' + json_data.data.num_months + '</strong> months';
                        add_subs_notification(message);
                        break;
                }
            }
        }
    }

    socket.onclose = function(e) {
        socket = null;
        isopen = false;
        setTimeout(connect_to_ws, 2500);
    }
}
