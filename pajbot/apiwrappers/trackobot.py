from pajbot.apiwrappers.base import BaseAPI
from pajbot.models.hsbet import HSGameOutcome


class TrackOBotGame:
    def __init__(self, id, outcome):
        self.id = id
        self.outcome = outcome

    def __eq__(self, other):
        if not isinstance(other, TrackOBotGame):
            return False
        return self.id == other.id


class TrackOBotAPI(BaseAPI):
    def __init__(self):
        super().__init__(base_url="https://trackobot.com/")

    def get_latest_game(self, username, token):
        response = self.get("/profile/history.json", params={"username": username, "token": token})

        if len(response["history"]) < 1:
            return None
        return TrackOBotGame(id=response["history"][0]["id"], outcome=HSGameOutcome[response["history"][0]["result"]])
