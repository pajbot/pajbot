from pajbot.apiwrappers.base import BaseAPI
from pajbot.apiwrappers.response_cache import ListSerializer
from pajbot.models.emote import Emote


class SevenTVAPI(BaseAPI):
    def __init__(self, redis):
        super().__init__(base_url="https://api.7tv.app/v2/", redis=redis)

    @staticmethod
    def parse_emotes(api_response_data):
        def get_url(emote_id, size):
            return f"https://cdn.7tv.app/emote/{emote_id}/{size}x"

        emotes = []
        for emote_data in api_response_data:
            emote_id = emote_data["id"]
            emotes.append(
                Emote(
                    code=emote_data["name"],
                    provider="7tv",
                    id=emote_id,
                    urls={
                        "1": get_url(emote_id, "1"),
                        "2": get_url(emote_id, "2"),
                        "3": get_url(emote_id, "3"),
                        "4": get_url(emote_id, "4"),
                    },
                )
            )
        return emotes

    def fetch_global_emotes(self):
        """Returns a list of global 7TV emotes in the standard Emote format."""
        query_string = """{{
            search_emotes(query: "", globalState: "only", page: {page}, limit: {limit}, pageSize: {page_size}) {{
                id
                name
            }}
        }}"""

        emotes_to_request = 150
        current_page = 1
        emotes_data = []
        while True:
            params = {
                "query": query_string.format(page=current_page, limit=emotes_to_request, page_size=emotes_to_request)
            }
            response = self.post("gql", json=params)
            emotes_data += response["data"]["search_emotes"]
            if len(response["data"]["search_emotes"]) < emotes_to_request:
                # We reached the end of the global emotes if the page isn't full
                break
            else:
                # fetch the next page of emotes
                current_page += 1

        return self.parse_emotes(emotes_data)

    def get_global_emotes(self, force_fetch=False):
        return self.cache.cache_fetch_fn(
            redis_key="api:7tv:global-emotes",
            fetch_fn=lambda: self.fetch_global_emotes(),
            serializer=ListSerializer(Emote),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )

    def fetch_channel_emotes(self, channel_name):
        """Returns a list of channel-specific 7TV emotes in the standard Emote format."""
        query_string = """{{
            user(id: "{channel_name}") {{
                emotes {{
                    id
                    name
                }}
            }}
        }}""".format(
            channel_name=channel_name
        )

        params = {"query": query_string}
        response = self.post("gql", json=params)

        if response["data"]["user"] is None:
            # user does not have any 7TV emotes
            return []

        return self.parse_emotes(response["data"]["user"]["emotes"])

    def get_channel_emotes(self, channel_name, force_fetch=False):
        return self.cache.cache_fetch_fn(
            redis_key=f"api:7tv:channel-emotes:{channel_name}",
            fetch_fn=lambda: self.fetch_channel_emotes(channel_name),
            serializer=ListSerializer(Emote),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )
