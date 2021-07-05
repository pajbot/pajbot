import html

import datetime
from requests import HTTPError

from pajbot import utils
from pajbot.apiwrappers.base import BaseAPI
from pajbot.apiwrappers.response_cache import ClassInstanceSerializer, ListSerializer


class QueUpQueueSong:
    def __init__(self, song_id, song_name, requester_id, requester_name, played_at, length):
        self.song_id = song_id
        self.song_name = song_name
        self.requester_id = requester_id
        # requester_name can be None if unknown
        self.requester_name = requester_name
        self.played_at = played_at
        self.length = length

    def jsonify(self):
        return {
            "song_id": self.song_id,
            "song_name": self.song_name,
            "requester_id": self.requester_id,
            "requester_name": self.requester_name,
            "played_at": self.played_at.timestamp() * 1000,
            "length": self.length.total_seconds() * 1000,
        }

    @staticmethod
    def from_json(json_data):
        song_id = json_data["song_id"]
        song_name = json_data["song_name"]
        requester_id = json_data["requester_id"]
        requester_name = json_data["requester_name"]
        played_at = utils.datetime_from_utc_milliseconds(json_data["played_at"])
        length = datetime.timedelta(milliseconds=json_data["length"])

        return QueUpQueueSong(
            song_id=song_id,
            song_name=song_name,
            requester_id=requester_id,
            requester_name=requester_name,
            played_at=played_at,
            length=length,
        )


class QueUpAPI(BaseAPI):
    def __init__(self, redis):
        super().__init__(base_url="https://api.queup.net", redis=redis)

    def fetch_room_id(self, room_name):
        response = self.get(["room", room_name])
        # if room is not found the API responds with status code 404 (an error will be raised)
        return response["data"]["_id"]

    def get_room_id(self, room_name):
        return self.cache.cache_fetch_fn(
            redis_key=f"api:queup:room-id:{room_name}",
            fetch_fn=lambda: self.fetch_room_id(room_name),
            expiry=1 * 60 * 60,  # 1 hour
        )

    def fetch_user_name(self, user_id):
        response = self.get(["user", user_id])
        return response["data"]["username"]

    def get_user_name(self, user_id):
        return self.cache.cache_fetch_fn(
            redis_key=f"api:queup:user-name:{user_id}",
            fetch_fn=lambda: self.fetch_user_name(user_id),
            expiry=10 * 60,  # 10 minutes
        )

    def fetch_song_link(self, song_id):
        response = self.get_response(["song", song_id, "redirect"], allow_redirects=False)
        return response.headers["Location"]

    def get_song_link(self, song_id):
        return self.cache.cache_fetch_fn(
            redis_key=f"api:queup:song-link:{song_id}",
            fetch_fn=lambda: self.fetch_song_link(song_id),
            expiry=1 * 60 * 60,  # 1 hour
        )

    def fetch_current_song(self, room_id):
        try:
            response = self.get(["room", room_id, "playlist", "active"])
        except HTTPError as e:
            if e.response.status_code == 404:
                # No songs in active queue.
                return None

            raise e

        song_id = response["data"]["song"]["songid"]
        song_name = html.unescape(response["data"]["songInfo"]["name"])
        requester_id = response["data"]["song"]["userid"]
        played_at = utils.datetime_from_utc_milliseconds(response["data"]["song"]["played"])
        length = datetime.timedelta(milliseconds=response["data"]["song"]["songLength"])

        return QueUpQueueSong(
            song_id=song_id,
            song_name=song_name,
            requester_id=requester_id,
            requester_name=None,
            played_at=played_at,
            length=length,
        )

    def get_current_song(self, room_id):
        return self.cache.cache_fetch_fn(
            redis_key=f"api:queup:current-song:{room_id}",
            fetch_fn=lambda: self.fetch_current_song(room_id),
            serializer=ClassInstanceSerializer(QueUpQueueSong),
            expiry=lambda response: 0 if response is None else 5,
        )

    def fetch_past_songs(self, room_id):
        response = self.get(["room", room_id, "playlist", "history"])

        def parse_song(song_json):
            song_id = song_json["_song"]["_id"]
            song_name = html.unescape(song_json["_song"]["name"])
            requester_id = song_json["_user"]["_id"]
            requester_name = song_json["_user"]["username"]
            played_at = utils.datetime_from_utc_milliseconds(song_json["played"])
            length = datetime.timedelta(milliseconds=song_json["_song"]["songLength"])

            return QueUpQueueSong(
                song_id=song_id,
                song_name=song_name,
                requester_id=requester_id,
                requester_name=requester_name,
                played_at=played_at,
                length=length,
            )

        return [parse_song(song_json) for song_json in response["data"]]

    def get_past_songs(self, room_id):
        return self.cache.cache_fetch_fn(
            redis_key=f"api:queup:past-songs:{room_id}",
            fetch_fn=lambda: self.fetch_past_songs(room_id),
            serializer=ListSerializer(QueUpQueueSong),
            expiry=5,
        )
