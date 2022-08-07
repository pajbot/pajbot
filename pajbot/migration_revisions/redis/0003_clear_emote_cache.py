import json


def up(redis, bot):
    # We have updated the Emote model, invalidate all emote caches
    # Specifically, the max_width and max_height properties are new and will be missing from the caches
    redis.delete(f"api:ffz:channel-emotes:{bot.streamer.login}")
    redis.delete("api:ffz:global-emotes")
    redis.delete(f"api:7tv:channel-emotes:{bot.streamer.login}")
    redis.delete("api:7tv:global-emotes")
    redis.delete(f"api:bttv:channel-emotes:{bot.streamer.id}")
    redis.delete("api:bttv:global-emotes")
    redis.delete(f"api:twitch:helix:channel-emotes:{bot.streamer.id}")
    redis.delete(f"api:twitch:helix:stream:by-id:{bot.streamer.id}")
    redis.delete("api:twitch:helix:global-emotes")

    current_emote_key = f"{bot.streamer.login}:current_quest_emote"
    current_emote_json = redis.get(current_emote_key)
    if current_emote_json is not None:
        # Force set max_width and max_height for the quest emote
        current_emote = json.loads(current_emote_json)
        current_emote["max_width"] = 112
        current_emote["max_height"] = 112
        redis.set(current_emote_key, json.dumps(current_emote))
