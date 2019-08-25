"""Migrate old bot token

Revision ID: a8c7ec3b898d
Revises: a8ad6e7fadd6
Create Date: 2019-08-04 16:07:00.746780

"""

# revision identifiers, used by Alembic.
import logging

import json

from pajbot.apiwrappers.authentication.access_token import UserAccessToken
from pajbot.db_migration import AlembicContext
from pajbot.managers.redis import RedisManager

revision = "a8c7ec3b898d"
down_revision = "a8ad6e7fadd6"
branch_labels = None
depends_on = None

log = logging.getLogger("pajbot")


def upgrade():
    redis = RedisManager.get()
    bot_name = AlembicContext.bot.nickname
    bot_user_id = AlembicContext.bot.bot_user_id
    old_redis_key = "{}:token".format(bot_name)
    new_redis_key = "authentication:user-access-token:{}".format(bot_user_id)

    if redis.exists(new_redis_key):
        log.info("Bot token migration: New token already present. Will delete old key if present")
        redis.delete(old_redis_key)
        return

    if not redis.exists(old_redis_key):
        log.info("Bot token migration: No old token to migrate.")
        return

    # this is a raw API response from the token get or refresh endpoint
    # sadly this is missing create time
    # to get the expiry time we refresh the token
    api_response = json.loads(redis.get(old_redis_key))

    # note: old_token will have the wrong created_at time
    old_token = UserAccessToken.from_api_response(api_response)
    new_token = old_token.refresh(AlembicContext.bot.twitch_id_api)
    redis.set(new_redis_key, json.dumps(new_token.jsonify()))

    log.info("Bot token migration: Successfully migrated old bot token")


def downgrade():
    redis = RedisManager.get()
    bot_name = AlembicContext.bot.nickname
    bot_user_id = AlembicContext.bot.bot_user_id
    old_redis_key = "{}:token".format(bot_name)
    new_redis_key = "authentication:user-access-token:{}".format(bot_user_id)

    if redis.exists(new_redis_key):
        redis.rename(new_redis_key, old_redis_key)
