import datetime
import logging

from pajbot.managers.db import DBManager
from pajbot.managers.redis import RedisManager
from pajbot.managers.user import UserManager
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.utils import time_method

log = logging.getLogger(__name__)


class ChattersModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Chatters'
    DESCRIPTION = 'Refreshes chatters'
    ENABLED_DEFAULT = True
    CATEGORY = 'Internal'
    HIDDEN = True
    SETTINGS = []

    def __init__(self):
        super().__init__()
        self.update_chatters_interval = 5
        self.initialized = False

    def update_chatters_stage1(self):
        return
        chatters = self.bot.twitchapi.get_chatters(self.bot.streamer)
        if len(chatters) > 0:
            self.bot.mainthread_queue.add(self.update_chatters_stage2, args=[chatters])

    @time_method
    def update_chatters_stage2(self, chatters):
        points = 1 if self.bot.is_online else 0

        log.debug('Updating {0} chatters'.format(len(chatters)))

        self.bot.stream_manager.update_chatters(chatters, self.update_chatters_interval)

        with RedisManager.pipeline_context() as pipeline:
            with DBManager.create_session_scope() as db_session:
                user_models = UserManager.get().bulk_load_user_models(chatters, db_session)
                users = []
                for username in chatters:
                    user_model = user_models.get(username, None)
                    user = UserManager.get().get_user(username, db_session=db_session, user_model=user_model, redis=pipeline)
                    users.append(user)

                more_update_data = {}
                if self.bot.is_online:
                    more_update_data['minutes_in_chat_online'] = self.update_chatters_interval
                else:
                    more_update_data['minutes_in_chat_offline'] = self.update_chatters_interval

                points_to_give_out = {}
                dt_now = datetime.datetime.now().timestamp()
                for user in users:
                    user._set_last_seen(dt_now)

                    num_points = points
                    if user.subscriber:
                        num_points *= 5
                    # TODO: Load user tags during the pipeline redis data fetch
                    if self.bot.streamer == 'forsenlol' and 'trumpsc_sub' in user.get_tags():
                        num_points *= 0.5

                    num_points = int(num_points)

                    if num_points not in points_to_give_out:
                        points_to_give_out[num_points] = []

                    points_to_give_out[num_points].append(user.username)

                    user.save(save_to_db=False)

                for num_points, usernames in points_to_give_out.items():
                    payload = {
                            User.points: User.points + num_points,
                            }
                    if self.bot.is_online:
                        payload[User.minutes_in_chat_online] = User.minutes_in_chat_online + self.update_chatters_interval
                    else:
                        payload[User.minutes_in_chat_offline] = User.minutes_in_chat_offline + self.update_chatters_interval
                    db_session.query(User).filter(User.username.in_(usernames)).\
                            update(payload, synchronize_session=False)

                pipeline.execute()

    """ NON-BATCHED VERSION
    @time_method
    def update_chatters_stage2(self, chatters):
        points = 1 if self.bot.is_online else 0

        log.debug('Updating {0} chatters'.format(len(chatters)))

        self.bot.stream_manager.update_chatters(chatters, self.update_chatters_interval)

        with RedisManager.pipeline_context() as pipeline:
            with DBManager.create_session_scope() as db_session:
                users = []
                for username in chatters:
                    user = UserManager.get().get_user(username, db_session)
                    user.queue_up_redis_calls(pipeline)
                    users.append(user)

                data = pipeline.execute()

                i = 0

                more_update_data = {}
                if self.bot.is_online:
                    more_update_data['minutes_in_chat_online'] = self.update_chatters_interval
                else:
                    more_update_data['minutes_in_chat_offline'] = self.update_chatters_interval

                points_to_give_out = {}
                for user in users:
                    l = len(UserRedis.FULL_KEYS)
                    inline_data = data[i:i + l]
                    user.load_redis_data(inline_data)
                    i += l

                    user.last_seen = datetime.datetime.now()

                    num_points = points
                    if user.subscriber:
                        num_points *= 5
                    if self.bot.streamer == 'forsenlol' and 'trumpsc_sub' in user.get_tags():
                        num_points *= 0.5

                    num_points = int(num_points)

                    if num_points not in points_to_give_out:
                        points_to_give_out[num_points] = []

                    points_to_give_out[num_points].append(user.username)

                    user.save()

                for num_points, usernames in points_to_give_out.items():
                    payload = {
                            User.points: User.points + num_points,
                            }
                    if self.bot.is_online:
                        payload[User.minutes_in_chat_online] = User.minutes_in_chat_online + self.update_chatters_interval
                    else:
                        payload[User.minutes_in_chat_offline] = User.minutes_in_chat_offline + self.update_chatters_interval
                    db_session.query(User).filter(User.username.in_(usernames)).\
                            update(payload, synchronize_session=False)

                pipeline.execute()
                """

    def enable(self, bot):
        """
        Update chatters every `update_chatters_interval' minutes.
        By default, this is set to run every 5 minutes.
        """
        self.bot = bot

        if bot:
            if not self.initialized:
                self.bot.execute_every(self.update_chatters_interval * 60,
                                   self.bot.action_queue.add,
                                   (self.update_chatters_stage1, ))
                self.initialized = True
            else:
                self.error('XXXXXXXXXX THIS SHOULD NOT HAPPEN')
                self.error('XXXXXXXXXX THIS SHOULD NOT HAPPEN')
                self.error('XXXXXXXXXX THIS SHOULD NOT HAPPEN')
                self.error('XXXXXXXXXX THIS SHOULD NOT HAPPEN')
                self.error('XXXXXXXXXX THIS SHOULD NOT HAPPEN')
                self.error('XXXXXXXXXX THIS SHOULD NOT HAPPEN')
