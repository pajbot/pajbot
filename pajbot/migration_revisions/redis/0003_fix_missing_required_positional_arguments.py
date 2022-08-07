def up(redis, bot):
    # invalidate all emote caches; they don't contain the max_width and max_height properties
    redis.delete(f"api:ffz:channel-emotes:{bot.streamer.login}")
    redis.delete("api:ffz:global-emotes")
    redis.delete(f"api:7tv:channel-emotes:{bot.streamer.login}")
    redis.delete("api:7tv:global-emotes")
    redis.delete(f"api:bttv:channel-emotes:{bot.streamer.id}")
    redis.delete("api:bttv:global-emotes")
    redis.delete(f"api:twitch:helix:channel-emotes:{bot.streamer.id}")
    redis.delete(f"api:twitch:helix:stream:by-id:{bot.streamer.id}")
    redis.delete("api:twitch:helix:global-emotes")
