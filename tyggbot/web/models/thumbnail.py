import json
import re
import argparse
import random
import urllib
import logging

import requests

log = logging.getLogger(__name__)

USHER_API = 'http://usher.twitch.tv/api/channel/hls/{channel}.m3u8?player=twitchweb' +\
    '&token={token}&sig={sig}&$allow_audio_only=true&allow_source=true' + \
    '&type=any&p={random}'
TOKEN_API = 'http://api.twitch.tv/api/channels/{channel}/access_token'

class StreamThumbnailWriter:
    original_path = 'static/images/highlights/{streamer}_{id}.jpg'
    thumbnail_path = 'static/images/highlights/{streamer}_{id}_tn.jpg'

    def __init__(self, streamer, ids):
        self.streamer = streamer
        self.ids = ids
        self.ts_path = '/tmp/ts_{}.ts'.format(self.streamer)

        m3u8_obj, url = self.get_live_stream()
        self.write_thumbnails(m3u8_obj, url)

    def get_token_and_signature(self):
        url = TOKEN_API.format(channel=self.streamer)
        r = requests.get(url)
        txt = r.text
        data = json.loads(txt)
        sig = data['sig']
        token = data['token']
        return token, sig

    def get_live_stream(self):
        import m3u8
        token, sig = self.get_token_and_signature()
        r = random.randint(0, 1E7)
        url = USHER_API.format(channel=self.streamer, sig=sig, token=token, random=r)
        r = requests.get(url)
        m3u8_obj = m3u8.loads(r.text)
        return m3u8_obj, url

    def write_thumbnails(self, m3u8_obj, url):
        for p in m3u8_obj.playlists:
            quality = p.media[0].name
            if quality == 'Source':
                uri = p.uri

                r = requests.get(uri)
                last_line = r.text.split('\n')[-2]
                parsed_uri = urllib.parse.urlparse(uri)
                short_path = '/'.join(parsed_uri.path.split('/')[:-1])
                ts_uri = '{uri.scheme}://{uri.netloc}{short_path}/{ts_path}'.format(uri=parsed_uri, short_path=short_path, ts_path=last_line)

                ts_r = requests.get(ts_uri, stream=True)
                if ts_r.status_code == 200:
                    with open(self.ts_path, 'wb') as f:
                        for chunk in ts_r:
                            f.write(chunk)

                import av
                from PIL import Image
                container = av.open(self.ts_path)
                video = next(s for s in container.streams if s.type == 'video')

                for packet in container.demux(video):
                    for frame in packet.decode():
                        im = frame.to_image()
                        im_tn = frame.to_image()
                        im_tn.thumbnail((240, 135))
                        for id in self.ids:
                            im.save(self.original_path.format(streamer=self.streamer, id=id))
                            im_tn.save(self.thumbnail_path.format(streamer=self.streamer, id=id))
                        return
