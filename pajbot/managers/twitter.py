import logging
from datetime import datetime
from threading import Thread

import tweepy

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
            self.bot.socket_manager.add_handler('twitter.follow', self.on_twitter_follow)
            self.bot.socket_manager.add_handler('twitter.unfollow', self.on_twitter_unfollow)

        if 'twitter' in bot.config:
            self.use_twitter_stream = 'streaming' in bot.config['twitter'] and bot.config['twitter']['streaming'] == '1'

            try:
                self.twitter_auth = tweepy.OAuthHandler(bot.config['twitter']['consumer_key'], bot.config['twitter']['consumer_secret'])
                self.twitter_auth.set_access_token(bot.config['twitter']['access_token'], bot.config['twitter']['access_token_secret'])

                self.twitter_client = tweepy.API(self.twitter_auth)

                if self.use_twitter_stream:
                    self.connect_to_twitter_stream()
                    bot.execute_every(60 * 5, self.check_twitter_connection)
            except:
                log.exception('Twitter authentication failed.')
                self.twitter_client = None

    def on_twitter_follow(self, data, conn):
        log.info('TWITTER FOLLOW')
        self.reload()

    def on_twitter_unfollow(self, data, conn):
        log.info('TWITTER UNFOLLOW')
        self.reload()

    def reload(self):
        if self.listener:
            self.listener.relevant_users = []
            with DBManager.create_session_scope() as db_session:
                for user in db_session.query(TwitterUser):
                    self.listener.relevant_users.append(user.username)

    def follow_user(self, username):
        """Add `username` to our relevant_users list."""
        if self.listener:
            if username not in self.listener.relevant_users:
                with DBManager.create_session_scope() as db_session:
                    db_session.add(TwitterUser(username))
                self.listener.relevant_users.append(username)
                log.info('Now following {0}'.format(username))
                return True
            else:
                log.warn('Already following {0}'.format(username))
        else:
            log.error('No twitter listener set up')
        return False

    def unfollow_user(self, username):
        """Stop following `username`, if we are following him."""
        if self.listener:
            if username in self.listener.relevant_users:
                self.listener.relevant_users.remove(username)

                with DBManager.create_session_scope() as db_session:
                    user = db_session.query(TwitterUser).filter_by(username=username).one_or_none()
                    if user:
                        db_session.delete(user)
                        log.info('No longer following {0}'.format(username))
                        return True
                    else:
                        log.warning('Trying to unfollow someone we are not following')
            else:
                log.warn('Trying to unfollow someone we are not following (2) {0}'.format(username))
        else:
            log.error('No twitter listener set up')

            return False

    def initialize_listener(self):
        if self.listener is None:
            class MyStreamListener(tweepy.StreamListener):
                def __init__(self, bot):
                    tweepy.StreamListener.__init__(self)
                    self.relevant_users = []
                    self.bot = bot

                def on_status(self, tweet):
                    if tweet.user.screen_name.lower() in self.relevant_users:
                        if not tweet.text.startswith('RT ') and tweet.in_reply_to_screen_name is None:
                            tw = tweet_prettify_urls(tweet)
                            self.bot.say('B) New cool tweet from {0}: {1}'.format(tweet.user.screen_name, tw.replace('\n', ' ')))

                def on_error(self, status):
                    log.warning('Unhandled in twitter stream: {0}'.format(status))

            self.listener = MyStreamListener(self.bot)
            self.reload()

    def initialize_twitter_stream(self):
        if self.twitter_stream is None:
            self.twitter_stream = tweepy.Stream(self.twitter_auth, self.listener, retry_420=3 * 60)

    def connect_to_twitter_stream(self):
        """Connect to the twitter stream.
        This will print out messages in the chat if a "relevant user" tweets something
        """
        try:
            self.initialize_listener()
            self.initialize_twitter_stream()

            self._thread = Thread(target=self._run, daemon=True)
            self._thread.start()
        except:
            log.exception('Exception caught while trying to connect to the twitter stream')

    def _run(self):
        try:
            self.twitter_stream.userstream(_with='followings', replies='all')
        except:
            log.exception('Exception caught in twitter stream _run')

    def check_twitter_connection(self):
        """Check if the twitter stream is running.
        If it's not running, try to restart it.
        """
        try:
            if self.twitter_stream.running is False:
                self.connect_to_twitter_stream()
        except:
            log.exception('Caught exception while checking twitter connection')

    def get_last_tweet(self, username):
        if self.twitter_client:
            try:
                public_tweets = self.twitter_client.user_timeline(username)
                for tweet in public_tweets:
                    if not tweet.text.startswith('RT ') and tweet.in_reply_to_screen_name is None:
                        tw = tweet_prettify_urls(tweet)
                        return '{0} ({1} ago)'.format(tw.replace('\n', ' '), time_since(datetime.now().timestamp(), tweet.created_at.timestamp(), format='short'))
            except Exception:
                log.exception('Exception caught while getting last tweet')
                return 'FeelsBadMan'
        else:
            return 'Twitter not set up FeelsBadMan'

        return 'FeelsBadMan'

    def quit(self):
        if self.twitter_stream:
            self.twitter_stream.disconnect()
            self._thread.join(1.0)
