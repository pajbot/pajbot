import json


def up(redis, bot):
    # invalidate bad emotes cache
    redis.delete("api:twitch:kraken:v5:global-emotes")
    redis.delete(f"api:twitch_emotes:channel-emotes:{bot.streamer.login}")
    redis.delete(f"api:ffz:channel-emotes:{bot.streamer.login}")
    redis.delete("api:ffz:global-emotes")

    current_emote_key = f"{bot.streamer.login}:current_quest_emote"
    current_emote_json = redis.get(current_emote_key)
    if current_emote_json is not None:
        # ensure emote id is a string
        current_emote = json.loads(current_emote_json)
        if not isinstance(current_emote["id"], str):
            current_emote["id"] = str(current_emote["id"])
            redis.set(current_emote_key, json.dumps(current_emote))
