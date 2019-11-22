import html


def _tweet_extract_text_with_expanded_urls(tweet):
    tweet_text = tweet.text
    for url in tweet.entities["urls"]:
        tweet_text = tweet_text.replace(url["url"], url["expanded_url"])

    return tweet_text


# Extract the text from a tweet and make it prettier
def stringify_tweet(tweet):
    tweet_text = _tweet_extract_text_with_expanded_urls(tweet)

    return html.unescape(tweet_text).replace("\n", " ")
