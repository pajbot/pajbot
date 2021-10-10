from typing import List

from pajbot.apiwrappers.base import BaseAPI


class TwitchTMIAPI(BaseAPI):
    def __init__(self) -> None:
        super().__init__(base_url="https://tmi.twitch.tv/")

    def get_chatter_logins_by_login(self, login: str) -> List[str]:
        response = self.get(["group", "user", login, "chatters"])

        # response =
        # {
        #   "_links": {},
        #   "chatter_count": 23,
        #   "chatters": {
        #     "broadcaster": [
        #       "edomer"
        #     ],
        #     "vips": [
        #       "felanbird",
        #       "magicbot321",
        #       "saprishxd",
        #       "titlechange_bot"
        #     ],
        #     "moderators": [
        #       "ali2465",
        #       "bukashka",
        #       "danolifer",
        #       "eeya_",
        #       "fallenv",
        #       "fancyy",
        #       "fausalol",
        #       "freelanzer",
        #       "nam_naam",
        #       "ourlordtalos",
        #       "randers",
        #       "razil0n",
        #       "rosethemagician",
        #       "streamelements",
        #       "thedangerousbros",
        #       "toastaddicted"
        #     ],
        #     "staff": [],
        #     "admins": [],
        #     "global_mods": [],
        #     "viewers": [
        #       "kraticevil",
        #       "orange_bean"
        #     ]
        #   }
        # }

        all_chatters = []
        for chatter_category in response["chatters"].values():
            all_chatters.extend(chatter_category)

        return all_chatters
