"""Reset current typeemote quest

Revision ID: a8ad6e7fadd6
Revises: 5f746af0a82d
Create Date: 2019-06-09 11:04:34.385778

"""

# revision identifiers, used by Alembic.
from pajbot.managers.redis import RedisManager
from pajbot.streamhelper import StreamHelper

revision = "a8ad6e7fadd6"
down_revision = "5f746af0a82d"
branch_labels = None
depends_on = None


streamer = StreamHelper.get_streamer()


def upgrade():
    with RedisManager.pipeline_context() as redis:
        redis.delete("{streamer}:current_quest_emote".format(streamer=streamer))
        redis.delete("{streamer}:current_quest".format(streamer=streamer))
        redis.delete("{streamer}:current_quest_progress".format(streamer=streamer))
        redis.delete("{streamer}:quests:finished".format(streamer=streamer))


def downgrade():
    with RedisManager.pipeline_context() as redis:
        redis.delete("{streamer}:current_quest_emote".format(streamer=streamer))
        redis.delete("{streamer}:current_quest".format(streamer=streamer))
        redis.delete("{streamer}:current_quest_progress".format(streamer=streamer))
        redis.delete("{streamer}:quests:finished".format(streamer=streamer))
