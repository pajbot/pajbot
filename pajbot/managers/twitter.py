import datetime
import logging
import threading

import tweepy

from pajbot import utils
from pajbot.managers.db import DBManager
from pajbot.models.twitter import TwitterUser
from pajbot.utils import time_since
from pajbot.utils import tweet_prettify_urls

log = logging.getLogger(__name__)


class TwitterManager:
    def __init__(self, bot):
        self.bot = bot

        self.twitter_client = None
        self.twitter_stream = None
        self.listener = None

        if self.bot:
            self.bot.socket_manager.add_handler("twitter.follow", self.on_twitter_follow)
            self.bot.socket_manager.add_handler("twitter.unfollow", self.on_twitter_unfollow)

        if "twitter" not in bot.config:
            return

        twitter_config = bot.config["twitter"]
        self.use_twitter_stream = "streaming" in twitter_config and twitter_config["streaming"] == "1"

        try:
            self.twitter_auth = tweepy.OAuthHandler(twitter_config["consumer_key"], twitter_config["consumer_secret"])
            self.twitter_auth.set_access_token(twitter_config["access_token"], twitter_config["access_token_secret"])

            self.twitter_client = tweepy.API(self.twitter_auth)

            if self.use_twitter_stream:
                self.check_twitter_connection()
                bot.execute_every(60 * 5, self.check_twitter_connection)
        except:
            log.exception("Twitter authentication failed.")
            self.twitter_client = None

    def on_twitter_follow(self, _data):
        log.info("TWITTER FOLLOW")
        self.reload()

    def on_twitter_unfollow(self, _data):
        log.info("TWITTER UNFOLLOW")
        self.reload()

    def reload(self):
        if self.listener:
            self.listener.relevant_users = []
            with DBManager.create_session_scope() as db_session:
                for user in db_session.query(TwitterUser):
                    self.listener.relevant_users.append(user.username)

    def follow_user(self, username):
        """Add `username` to our relevant_users list."""
        if not self.listener:
            log.error("No twitter listener set up")
            return False

        if username in self.listener.relevant_users:
            log.warning("Already following {0}".format(username))
            return False

        with DBManager.create_session_scope() as db_session:
            db_session.add(TwitterUser(username))
            self.listener.relevant_users.append(username)
            log.info("Now following {0}".format(username))

        return True

    def unfollow_user(self, username):
        """Stop following `username`, if we are following him."""
        if not self.listener:
            log.error("No twitter listener set up")
            return False

        if username not in self.listener.relevant_users:
            log.warning("Trying to unfollow someone we are not following (2) {0}".format(username))
            return False

        self.listener.relevant_users.remove(username)

        with DBManager.create_session_scope() as db_session:
            user = db_session.query(TwitterUser).filter_by(username=username).one_or_none()
            if not user:
                log.warning("Trying to unfollow someone we are not following")
                return False

            db_session.delete(user)
            log.info("No longer following {0}".format(username))

        return True

    def initialize_listener(self):
        if self.listener is None:

            class MyStreamListener(tweepy.StreamListener):
                def __init__(self, bot):
                    tweepy.StreamListener.__init__(self)
                    self.relevant_users = []
                    self.bot = bot

                def on_status(self, status):
                    log.debug("On status from tweepy: %s", status.text)
                    if status.user.screen_name.lower() in self.relevant_users:
                        if not status.text.startswith("RT ") and status.in_reply_to_screen_name is None:
                            tw = tweet_prettify_urls(status)
                            self.bot.say(
                                "B) New cool tweet from {0}: {1}".format(status.user.screen_name, tw.replace("\n", " "))
                            )

                def on_error(self, status_code):
                    log.warning("Unhandled in twitter stream: %s", status_code)
                    return super().on_error(status_code)

            self.listener = MyStreamListener(self.bot)
            self.reload()

    def initialize_twitter_stream(self):
        if self.twitter_stream is None:
            self.twitter_stream = tweepy.Stream(self.twitter_auth, self.listener, retry_420=3 * 60)

    def _run_twitter_stream(self):
        self.initialize_listener()
        self.initialize_twitter_stream()

        user_ids = []
        with DBManager.create_session_scope() as db_session:
            for user in db_session.query(TwitterUser):
                twitter_user = self.twitter_client.get_user(user.username)
                if twitter_user:
                    user_ids.append(twitter_user.id_str)

        if not user_ids:
            return

        try:
            self.twitter_stream.filter(follow=user_ids, is_async=False)
        except:
            log.exception("Exception caught in twitter stream _run")

    def check_twitter_connection(self):
        """Check if the twitter stream is running.
        If it's not running, try to restart it.
        """
        if self.twitter_stream and self.twitter_stream.running:
            return

        try:
            t = threading.Thread(target=self._run_twitter_stream, name="Twitter")
            t.daemon = True
            t.start()
        except:
            log.exception("Caught exception while checking twitter connection")

    def get_last_tweet(self, username):
        if self.twitter_client:
            try:
                public_tweets = self.twitter_client.user_timeline(username)
                for tweet in public_tweets:
                    if not tweet.text.startswith("RT ") and tweet.in_reply_to_screen_name is None:
                        tw = tweet_prettify_urls(tweet)
                        # Tweepy returns naive datetime object (but it's always UTC)
                        # .replace() makes it timezone-aware :)
                        created_at = tweet.created_at.replace(tzinfo=datetime.timezone.utc)
                        return "{0} ({1} ago)".format(
                            tw.replace("\n", " "),
                            time_since(utils.now().timestamp(), created_at.timestamp(), time_format="short"),
                        )
            except Exception:
                log.exception("Exception caught while getting last tweet")
                return "FeelsBadMan"
        else:
            return "Twitter not set up FeelsBadMan"

        return "FeelsBadMan"

    def quit(self):
        if self.twitter_stream:
            self.twitter_stream.disconnect()
