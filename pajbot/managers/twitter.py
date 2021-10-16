from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Union

import datetime
import json
import logging
import threading

from pajbot.managers.db import DBManager
from pajbot.models.twitter import TwitterUser
from pajbot.utils import now, stringify_tweet, time_since, tweet_provider_stringify_tweet

import tweepy
from autobahn.twisted.websocket import WebSocketClientFactory, WebSocketClientProtocol
from twisted.internet.protocol import ReconnectingClientFactory

if TYPE_CHECKING:
    from pajbot.bot import Bot
    from pajbot.models.sock import HandlerParam

log = logging.getLogger(__name__)


class ClientProtocol(WebSocketClientProtocol):
    def __init__(self, manager: PBTwitterManager) -> None:
        super().__init__()

        self.manager = manager

    def onOpen(self) -> None:
        self.manager.client = self

        if self.manager.tweepy is None:
            log.warning(
                "Unable to initialize tweet-provider connection since local twitter credentials are not configured"
            )
            return

        user_ids = [self.manager.tweepy.get_user(screen_name=e).id for e in self.manager.relevant_users]

        msg = {"type": "set_subscriptions", "data": user_ids}

        self.sendMessage(json.dumps(msg).encode("utf8"))

    def onMessage(self, payload: str, isBinary: bool) -> None:
        if isBinary:
            return

        message = json.loads(payload)
        if message["type"] == "tweet":
            tweet = message["data"]
            if (
                tweet["user"]["screen_name"].lower() in self.manager.relevant_users
                and not tweet["text"].startswith("RT ")
                and tweet["in_reply_to_screen_name"] is None
            ):
                tweet_message = tweet_provider_stringify_tweet(tweet)
                self.manager.bot.say(f"B) New cool tweet from {tweet['user']['screen_name']}: {tweet_message}")
                log.debug(f"Got tweet: {message['data']}")
        else:
            log.debug(f"Unhandled message from tweet-provider: {message}")

    def onClose(self, wasClean: bool, code: int, reason: str) -> None:
        log.info(f"Disconnected from tweet-provider: {reason}")


class ClientFactory(WebSocketClientFactory, ReconnectingClientFactory):
    maxDelay = 30
    manager: Optional[PBTwitterManager] = None

    def buildProtocol(self, addr):
        if self.manager is None:
            raise ValueError("ClientFactory's manager not initialized")

        proto = ClientProtocol(self.manager)
        proto.factory = self
        return proto

    def clientConnectionFailed(self, connector, reason) -> None:
        log.debug(f"Connection failed to PBTwitterManager: {reason}")
        self.retry(connector)

    def clientConnectionLost(self, connector, reason) -> None:
        log.debug(f"Connection lost to PBTwitterManager: {reason}")
        self.retry(connector)


class MyStreamListener(tweepy.Stream):
    def __init__(self, bot: Bot):
        self.relevant_users: List[str] = []
        self.bot = bot

        if "twitter" not in bot.config:
            return

        twitter_config = bot.config["twitter"]

        super().__init__(
            twitter_config["consumer_key"],
            twitter_config["consumer_secret"],
            twitter_config["access_token"],
            twitter_config["access_token_secret"],
        )

    def on_status(self, status: tweepy.models.Status) -> None:
        if (
            status.user.screen_name.lower() in self.relevant_users
            and not status.text.startswith("RT ")
            and status.in_reply_to_screen_name is None
        ):
            log.debug("On status from tweepy: %s", status.text)
            tweet_message = stringify_tweet(status)
            self.bot.say(f"B) New cool tweet from {status.user.screen_name}: {tweet_message}")

    def on_request_error(self, status_code: int) -> None:
        log.warning("Unhandled in twitter stream: %s", status_code)

        super().on_error(status_code)


class GenericTwitterManager:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

        self.twitter_client: Optional[tweepy.API] = None
        self.listener: Union[None, MyStreamListener, PBTwitterManager] = None

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
        except:
            log.exception("Twitter authentication failed.")

    def on_twitter_follow(self, _data: HandlerParam) -> None:
        log.info("TWITTER FOLLOW")
        self.reload()

    def on_twitter_unfollow(self, _data: HandlerParam) -> None:
        log.info("TWITTER UNFOLLOW")
        self.reload()

    def reload(self) -> None:
        if self.listener:
            self.listener.relevant_users = []
            with DBManager.create_session_scope() as db_session:
                for user in db_session.query(TwitterUser):
                    if user.username is None:
                        log.warning(f"Twitter user with DB ID {user.id} has a null username")
                        continue

                    self.listener.relevant_users.append(user.username)

    def follow_user(self, username: str) -> bool:
        """Add `username` to our relevant_users list."""
        if not self.listener:
            log.error("No twitter listener set up")
            return False

        if username in self.listener.relevant_users:
            log.warning(f"Already following {username}")
            return False

        with DBManager.create_session_scope() as db_session:
            db_session.add(TwitterUser(username))
            self.listener.relevant_users.append(username)
            log.info(f"Now following {username}")

        return True

    def unfollow_user(self, username: str) -> bool:
        """Stop following `username`, if we are following him."""
        if not self.listener:
            log.error("No twitter listener set up")
            return False

        if username not in self.listener.relevant_users:
            log.warning(f"Trying to unfollow someone we are not following (2) {username}")
            return False

        self.listener.relevant_users.remove(username)

        with DBManager.create_session_scope() as db_session:
            user = db_session.query(TwitterUser).filter_by(username=username).one_or_none()
            if not user:
                log.warning("Trying to unfollow someone we are not following")
                return False

            db_session.delete(user)
            log.info(f"No longer following {username}")

        return True

    def get_last_tweet(self, username: str) -> str:
        if self.twitter_client:
            try:
                public_tweets = self.twitter_client.user_timeline(screen_name=username)
                for tweet in public_tweets:
                    if not tweet.text.startswith("RT ") and tweet.in_reply_to_screen_name is None:
                        # Tweepy returns naive datetime object (but it's always UTC)
                        # .replace() makes it timezone-aware :)
                        created_at = tweet.created_at.replace(tzinfo=datetime.timezone.utc)
                        tweet_message = stringify_tweet(tweet)
                        return f"{tweet_message} ({time_since(now().timestamp(), created_at.timestamp(), time_format='short')} ago)"
            except Exception:
                log.exception("Exception caught while getting last tweet")
                return "FeelsBadMan"
        else:
            return "Twitter not set up FeelsBadMan"

        return "FeelsBadMan"

    def quit(self) -> None:
        pass


# TwitterManager loads live tweets from Twitter's Streaming API
class TwitterManager(GenericTwitterManager):
    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)

        self.twitter_stream: Optional[MyStreamListener] = None

        if "twitter" not in bot.config:
            return

        try:
            if self.use_twitter_stream:
                self.check_twitter_connection()
                bot.execute_every(60 * 5, self.check_twitter_connection)
        except:
            log.exception("Twitter authentication failed.")

    def initialize_twitter_stream(self) -> None:
        if self.twitter_stream is None:
            self.twitter_stream = MyStreamListener(self.bot)
            self.listener = self.twitter_stream

            self.reload()

    def _run_twitter_stream(self) -> None:
        if self.twitter_client is None:
            log.warn("Unable to run twitter stream: local twitter client not configured")
            return

        self.initialize_twitter_stream()

        if self.twitter_stream is None:
            log.warn("Unable to run twitter stream: twitter stream failed to initialize")
            return

        user_ids = []
        with DBManager.create_session_scope() as db_session:
            for user in db_session.query(TwitterUser):
                twitter_user: tweepy.User = self.twitter_client.get_user(screen_name=user.username)
                if twitter_user:
                    user_ids.append(twitter_user.id_str)

        if not user_ids:
            return

        try:
            self.twitter_stream.filter(follow=user_ids, threaded=False)
        except:
            log.exception("Exception caught in twitter stream _run")

    def check_twitter_connection(self) -> None:
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

    def quit(self) -> None:
        if self.twitter_stream:
            self.twitter_stream.disconnect()


# PBTwitterManager reads live tweets from a pajbot tweet-provider (https://github.com/pajbot/tweet-provider) instead of Twitter's streaming API
class PBTwitterManager(GenericTwitterManager):
    client: Optional[ClientProtocol] = None
    tweepy: Optional[tweepy.API] = None

    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)

        self.relevant_users: List[str] = []

        PBTwitterManager.bot = bot
        PBTwitterManager.tweepy = self.twitter_client

        self.listener = self

        if "twitter" not in bot.config:
            return

        self.reload()

        log.info("pajbot twitter manager initialized")

        from twisted.internet import reactor

        twitter_config = bot.config["twitter"]
        tweet_provider_host = twitter_config.get("tweet_provider_host", "127.0.0.1")
        tweet_provider_port = int(twitter_config.get("tweet_provider_port", 2356))
        tweet_provider_protocol = twitter_config.get("tweet_provider_protocol", "ws")

        factory = ClientFactory(f"{tweet_provider_protocol}://{tweet_provider_host}:{tweet_provider_port}")
        factory.manager = self

        reactor.connectTCP(tweet_provider_host, tweet_provider_port, factory)  # type:ignore

    def follow_user(self, username: str) -> bool:
        if self.twitter_client is None:
            log.warn("Unable to forward follow to twitter_manager: local twitter client not configured")
            return False

        ws_client = PBTwitterManager.client

        if ws_client is None:
            log.warn("Unable to forward follow to twitter_manager: not connected")
            return False

        ret = super().follow_user(username)
        if ret is True:
            user = self.twitter_client.get_user(screen_name=username)
            msg = {"type": "insert_subscriptions", "data": [user.id]}
            ws_client.sendMessage(json.dumps(msg).encode("utf8"))

        return ret

    def unfollow_user(self, username: str) -> bool:
        if self.twitter_client is None:
            log.warn("Unable to forward unfollow to twitter_manager: local twitter client not configured")
            return False

        ws_client = PBTwitterManager.client

        if ws_client is None:
            log.warn("Unable to forward unfollow to twitter_manager: not connected")
            return False

        ret = super().unfollow_user(username)
        if ret is True:
            user = self.twitter_client.get_user(screen_name=username)
            msg = {"type": "remove_subscriptions", "data": [user.id]}
            ws_client.sendMessage(json.dumps(msg).encode("utf8"))

        return ret
