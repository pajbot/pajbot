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
