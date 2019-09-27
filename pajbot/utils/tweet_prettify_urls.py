def tweet_prettify_urls(tweet):
    tweet_text = tweet.text
    for url in tweet.entities["urls"]:
        tweet_text = tweet_text.replace(url["url"], url["expanded_url"])

    return tweet_text
