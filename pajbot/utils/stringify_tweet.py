from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

import html

if TYPE_CHECKING:
    from tweepy import Tweet


def _tweet_extract_text_with_expanded_urls(tweet: Tweet) -> str:
    tweet_text: str = tweet.text
    for url in tweet.entities["urls"]:
        tweet_text = tweet_text.replace(url["url"], url["expanded_url"])

    return tweet_text


# Extract the text from a tweet and make it prettier
def stringify_tweet(tweet: Tweet) -> str:
    tweet_text = _tweet_extract_text_with_expanded_urls(tweet)

    return html.unescape(tweet_text).replace("\n", " ")


def _tweet_provider_tweet_extract_text_with_expanded_urls(tweet: Dict[str, Any]) -> str:
    tweet_text: str = tweet["text"]
    for url in tweet["urls"]:
        tweet_text = tweet_text.replace(url["url"], url["expanded_url"])

    return tweet_text


# Extract the text from a tweet and make it prettier
def tweet_provider_stringify_tweet(tweet: Dict[str, Any]) -> str:
    tweet_text = _tweet_provider_tweet_extract_text_with_expanded_urls(tweet)

    return html.unescape(tweet_text).replace("\n", " ")
