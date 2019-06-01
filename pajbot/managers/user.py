import logging
from contextlib import contextmanager

from pajbot.managers.db import DBManager
from pajbot.models.user import User
from pajbot.models.user import UserCombined
from pajbot.models.user import UserSQLCache
from pajbot.utils import time_method

log = logging.getLogger(__name__)


class UserManager:
    data = {}
    _instance = None

    def __init__(self):
        UserSQLCache.init()
        UserManager._instance = self

    @staticmethod
    def get():
        return UserManager._instance

    def save(self, user):
        """ Saves all data for a user.
        This means cached data (like his debts) and SQL """
        self.data[user.username] = user.save()

    @staticmethod
    def get_static(username, db_session=None, user_model=None, redis=None):
        return UserCombined(username, db_session=db_session, user_model=user_model, redis=redis)

    def get_user(self, username, db_session=None, user_model=None, redis=None):
        """ Return to call UserManager.save(user.username) an the user object manually when done with if. """
        user = UserCombined(username, db_session=db_session, user_model=user_model, redis=redis)
        user.load(**self.data.get(username, {}))
        return user

    @contextmanager
    def get_user_context(self, username):
        try:
            user = UserCombined(username)
            user.load(**self.data.get(username, {}))

            yield user
        except:
            log.exception("Uncaught exception in UserManager::get_user({})".format(username))
        finally:
            self.save(user)

    def __getitem__(self, username):
        return self.get_user(username)

    @contextmanager
    def find_context(self, username, db_session=None):
        try:
            user = self.find(username, db_session=db_session)
            yield user
        except:
            log.exception("Uncaught exception in UserManager::find_context({})".format(username))
        finally:
            if user:
                self.save(user)

    @staticmethod
    def find_static(username, db_session=None):
        """
        Attempts to find the user with the given username.

        Arguments:
        username - Username of the user we're trying to find. Case-insensitive.

        Returns a user object if the user already existed, otherwise return None
        """

        # from pajbot.utils import print_traceback
        # print_traceback()

        # log.debug('UserManager::find({})'.format(username))

        # Return None if the username is an empty string!
        if username == "":
            return None

        # Replace any occurances of @ in the username
        # This helps non-bttv-users who tab-complete usernames
        username = username.replace("@", "")

        # This will be used when we access the cache dictionary
        username_lower = username.lower()

        # Check for the username in the database
        user = UserManager.get_static(username_lower, db_session=db_session)
        if user.new:
            return None
        return user

    def find(self, username, db_session=None):
        """
        Attempts to find the user with the given username.

        Arguments:
        username - Username of the user we're trying to find. Case-insensitive.

        Returns a user object if the user already existed, otherwise return None
        """

        # from pajbot.utils import print_traceback
        # print_traceback()

        # log.debug('UserManager::find({})'.format(username))

        # Return None if the username is an empty string!
        if username == "":
            return None

        # Replace any occurances of @ in the username
        # This helps non-bttv-users who tab-complete usernames
        username = username.replace("@", "")

        # This will be used when we access the cache dictionary
        username_lower = username.lower()

        # Check for the username in the database
        user = self.get_user(username_lower, db_session=db_session)
        if user.new:
            return None
        return user

    @time_method
    def reset_subs(self):
        """ Returns how many subs were reset """
        with DBManager.create_session_scope() as db_session:
            return (
                db_session.query(User)
                .filter_by(subscriber=True)
                .update({User.subscriber: False}, synchronize_session=False)
            )

    @time_method
    def update_subs(self, subs):
        """
        subs is a list of usernames
        """

        with DBManager.create_session_scope() as db_session:
            subs = set(subs)
            for user in db_session.query(User).filter(User.username.in_(subs)):
                try:
                    subs.remove(user.username)
                except:
                    pass

                user.subscriber = True

            for username in subs:
                # New user!
                user = User(username=username)
                user.subscriber = True

                db_session.add(user)

    @staticmethod
    def bulk_load_user_models(usernames, db_session):
        users = db_session.query(User).filter(User.username.in_(usernames))
        return {user.username: user for user in users}
