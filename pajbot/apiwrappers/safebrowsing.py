from pajbot.apiwrappers.apiwrappers import BaseApi
from pajbot.bot import Bot


class SafeBrowsingApi(BaseApi):
    def __init__(self, api_key):
        super().__init__("https://safebrowsing.googleapis.com/v4/")
        self.session.params["key"] = api_key

    def is_url_bad(self, url):
        resp = self.post(
            "/threatMatches:find",
            json={
                "client": {"clientId": "pajbot1", "clientVersion": Bot.version},
                "threatInfo": {
                    "threatTypes": [
                        "THREAT_TYPE_UNSPECIFIED",
                        "MALWARE",
                        "SOCIAL_ENGINEERING",
                        "UNWANTED_SOFTWARE",
                        "POTENTIALLY_HARMFUL_APPLICATION",
                    ],
                    "platformTypes": [
                        "PLATFORM_TYPE_UNSPECIFIED",
                        "WINDOWS",
                        "LINUX",
                        "ANDROID",
                        "OSX",
                        "IOS",
                        "ANY_PLATFORM",
                        "ALL_PLATFORMS",
                        "CHROME",
                    ],
                    "threatEntryTypes": ["THREAT_ENTRY_TYPE_UNSPECIFIED", "URL", "EXECUTABLE"],
                    "threatEntries": [{"url": url}],
                },
            },
        )

        # good response: {} or {"matches":[]}
        # bad response: {"matches":[{ ... }]}

        return len(resp.get("matches", [])) > 0
