def up(redis, bot):
    redis.delete("{streamer}:viewer_data".format(streamer=bot.streamer))
