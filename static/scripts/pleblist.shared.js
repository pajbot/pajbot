function parse_youtube_id_from_url(url)
{
    var parsed_uri = parseUri(url);

    var youtube_id = false;

    if (parsed_uri.host.indexOf('youtu.be') !== -1) {
        youtube_id = parsed_uri.path.substring(1);
    } else if (parsed_uri.host.indexOf('youtube.com') !== -1) {
        youtube_id = parsed_uri.queryKey.v;
    }

    return youtube_id;
}

function parse_imgur_data_from_url(parsed_uri)
{
    var imgur_data = {'album': false, 'id': false, 'new_url': false};

    parsed_uri = parseUri(parsed_uri.source.replace(/\/gallery/g, '').replace(/\/r\/([a-zA-Z0-9_]+)/g, ''));

    if (parsed_uri.host.endsWith('imgur.com') === true) {
        // Successfully found an imgur URL
        // Decide whether it's an album or not
        if (parsed_uri.path.startsWith('/a/')) {
            // This is an album!
            imgur_data.album = true;
            imgur_data.id = parsed_uri.path.substr(3).split('.')[0];
        } else {
            // a normal image
            imgur_data.id = parsed_uri.path.substr(1).split('.')[0];
            imgur_data.new_url = 'http://i.imgur.com/' + imgur_data.id + 'h.jpg';
        }
    }

    return imgur_data;
}
