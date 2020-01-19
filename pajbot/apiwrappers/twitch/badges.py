import logging

from pajbot.apiwrappers.response_cache import ClassInstanceSerializer
from pajbot.apiwrappers.base import BaseAPI

log = logging.getLogger(__name__)


class BadgeNotFoundError(ValueError):
    pass


class BadgeVersion:
    def __init__(self, image_url_1x, image_url_2x, image_url_4x, description, title):
        self.image_url_1x = image_url_1x
        self.image_url_2x = image_url_2x
        self.image_url_4x = image_url_4x
        self.description = description
        self.title = title

    def jsonify(self):
        return {
            "image_url_1x": self.image_url_1x,
            "image_url_2x": self.image_url_2x,
            "image_url_4x": self.image_url_4x,
            "description": self.description,
            "title": self.title,
        }

    @staticmethod
    def from_json(json_data):
        image_url_1x = json_data["image_url_1x"]
        image_url_2x = json_data["image_url_2x"]
        image_url_4x = json_data["image_url_4x"]
        description = json_data["description"]
        title = json_data["title"]
        return BadgeVersion(
            image_url_1x=image_url_1x,
            image_url_2x=image_url_2x,
            image_url_4x=image_url_4x,
            description=description,
            title=title,
        )


class BadgeSet:
    def __init__(self, set_id, versions):
        self.set_id = set_id
        self.versions = versions

    def jsonify(self):
        return {
            "set_id": self.set_id,
            "versions": {
                badge_version_id: badge_version.jsonify() for badge_version_id, badge_version in self.versions.items()
            },
        }

    @staticmethod
    def from_json(json_data):
        set_id = json_data["set_id"]
        versions = {
            badge_version_id: BadgeVersion.from_json(badge_version_json)
            for badge_version_id, badge_version_json in json_data["versions"].items()
        }

        return BadgeSet(set_id=set_id, versions=versions)


class BadgeSets(dict):
    def jsonify(self):
        return {badge_set_id: badge_set.jsonify() for badge_set_id, badge_set in self.items()}

    @staticmethod
    def from_json(json_data):
        sets = {badge_set_id: BadgeSet.from_json(badge_set_json) for badge_set_id, badge_set_json in json_data.items()}

        return BadgeSets(sets)


# https://discuss.dev.twitch.tv/t/beta-badge-api/6388
class TwitchBadgesAPI(BaseAPI):
    def __init__(self, redis):
        super().__init__(base_url="https://badges.twitch.tv/v1/", redis=redis)

    def _fetch_channel_badge_sets(self, channel_id):
        response = self.get(["badges", "channels", channel_id, "display"], {"language": "en"})

        json_badge_sets = response["badge_sets"]
        badge_sets = BadgeSets()

        for badge_set_id, json_badge_set in json_badge_sets.items():
            badge_set_versions = {}
            for version_id, json_badge_version in json_badge_set["versions"].items():
                badge_set_versions[version_id] = BadgeVersion(
                    image_url_1x=json_badge_version["image_url_1x"],
                    image_url_2x=json_badge_version["image_url_2x"],
                    image_url_4x=json_badge_version["image_url_4x"],
                    description=json_badge_version["description"],
                    title=json_badge_version["title"],
                )

            badge_sets[badge_set_id] = BadgeSet(set_id=badge_set_id, versions=badge_set_versions)

        return badge_sets

    def get_channel_badge_sets(self, channel_id):
        return self.cache.cache_fetch_fn(
            redis_key=f"api:twitch:badges:channel-badge-sets:{channel_id}",
            fetch_fn=lambda: self._fetch_channel_badge_sets(channel_id),
            serializer=ClassInstanceSerializer(BadgeSets),
            expiry=60 * 60,
        )

    def get_channel_subscriber_badge(self, channel_id, version="0"):
        badge_sets = self.get_channel_badge_sets(channel_id)

        if "subscriber" not in badge_sets:
            raise BadgeNotFoundError(f"Channel({channel_id}) does not have any subscriber badges")

        if version not in badge_sets["subscriber"].versions:
            raise BadgeNotFoundError(f"Channel({channel_id}) does not have a subscriber badge with this version")

        return badge_sets["subscriber"].versions[version]
