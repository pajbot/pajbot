def up(redis, bot):
    redis.delete(f"{bot.streamer}:viewer_data")
