def up(redis, bot):
    redis.delete(f"{bot.streamer.login}:viewer_data")
