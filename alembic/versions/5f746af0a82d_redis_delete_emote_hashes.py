"""Redis: Delete emote hashes

Revision ID: 5f746af0a82d
Revises: 186928676dbc
Create Date: 2019-06-04 19:07:25.109751

"""


from pajbot.managers.redis import RedisManager
from pajbot.streamhelper import StreamHelper


# revision identifiers, used by Alembic.
revision = "5f746af0a82d"
down_revision = "186928676dbc"
branch_labels = None
depends_on = None

streamer = StreamHelper.get_streamer()


def upgrade():
    with RedisManager.pipeline_context() as redis:
        redis.delete("{streamer}:emotes:ffz_channel_emotes".format(streamer=streamer))
        redis.delete("{streamer}:emotes:bttv_channel_emotes".format(streamer=streamer))
        redis.delete("global:emotes:ffz_global")
        redis.delete("global:emotes:bttv_global")


def downgrade():
    with RedisManager.pipeline_context() as redis:
        redis.delete("{streamer}:emotes:twitch_channel_emotes".format(streamer=streamer))
        redis.delete("{streamer}:emotes:ffz_channel_emotes".format(streamer=streamer))
        redis.delete("{streamer}:emotes:bttv_channel_emotes".format(streamer=streamer))
        redis.delete("global:emotes:twitch_global_emotes")
        redis.delete("global:emotes:ffz_global_emotes")
        redis.delete("global:emotes:bttv_global_emotes")
