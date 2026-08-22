import tweepy
from django.conf import settings

class TweetClient:
    """
    A lightweight wrapper around the Tweepy Client used to interact with the
    Twitter (X) API from within the PlanetPress platform.

    This class centralizes authentication using API credentials stored in
    Django settings and provides simple helper methods for posting content
    to Twitter. It is primarily used to automatically publish tweets when
    an article is approved by an editor or when other system events trigger
    social media updates.

    Attributes:
        client (tweepy.Client):
            An authenticated Tweepy client instance configured with the
            application's API keys and access tokens.

    Methods:
        tweet_text(text):
            Posts a plain‑text tweet to the authenticated Twitter account.

            Args:
                text (str): The message to publish as a tweet.

            Returns:
                None. The underlying Tweepy client handles the API response.
    """
    def __init__(self):
        self.client = tweepy.Client(
            consumer_key=settings.TWITTER_API_KEY,
            consumer_secret=settings.TWITTER_API_SECRET,
            access_token=settings.TWITTER_ACCESS_TOKEN,
            access_token_secret=settings.TWITTER_ACCESS_SECRET
        )

    def tweet_text(self, text):
        self.client.create_tweet(text=text)