import logging

from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class LeagueRankModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "LeagueRank module"
    DESCRIPTION = "Enable this to check the rank of others in League of Legends in the chat."
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="riot_api_key",
            label="Riot developer api key",
            type="text",
            required=True,
            placeholder="i.e. 1e3415de-1234-5432-f331-67abb0454d12",
            default="",
        ),
        ModuleSetting(
            key="default_summoner",
            label="Default summoner name",
            type="text",
            required=True,
            placeholder="i.e. moregainfreeman (remove space)",
            default="",
        ),
        ModuleSetting(
            key="default_region",
            label="Default region, valid options: br1, eun1, euw1, jp1, kr, la1, la2, na1, oc1, tr1, ru",
            type="text",
            required=True,
            placeholder="i.e. euw/eune/na/br/oce",
            default="",
        ),
        ModuleSetting(
            key="online_global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=15,
            constraints={"min_value": 0, "max_value": 120},
        ),
        ModuleSetting(
            key="online_user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=30,
            constraints={"min_value": 0, "max_value": 240},
        ),
    ]

    def load_commands(self, **options):
        self.commands["lolrank"] = Command.raw_command(
            self.league_rank,
            delay_all=self.settings["online_global_cd"],
            delay_user=self.settings["online_user_cd"],
            description="Check streamer's or other players League of Legends rank in chat.",
            examples=[
                CommandExample(
                    None,
                    "Check streamer's rank",
                    chat="user:!lolrank\n"
                    "bot: The Summoner Moregain Freeman on region EUW1 is currently in PLATINUM IV with 62 LP 4Head",
                    description="Bot says broadcaster's region, League-tier, division and LP",
                ).parse(),
                CommandExample(
                    None,
                    "Check other player's rank on default region",
                    chat="user:!lolrank forsen\n"
                    "bot: The Summoner forsen on region EUW1 is currently in SILVER IV with 36 LP 4Head",
                    description="Bot says player's region, League-tier, division and LP",
                ).parse(),
                CommandExample(
                    None,
                    "Check other player's rank on another region",
                    chat="user:!lolrank imaqtpie na1\n"
                    "bot: The Summoner Imaqtpie on region NA1 is currently in CHALLENGER I with 441 LP 4Head",
                    description="Bot says player's region, League-tier, division and LP. Other regions to use as arguments: br1, eun1, euw1, jp1, kr, la1, la2, na1, oc1, tr1, ru",
                ).parse(),
            ],
        )
        self.commands["ranklol"] = self.commands["lolrank"]
        self.commands["leaguerank"] = self.commands["lolrank"]

    def league_rank(self, bot, source, message, **rest):
        try:
            from riotwatcher import LolWatcher, ApiError
        except ImportError:
            log.error("Missing required module for League Rank module: riotwatcher")
            return False

        riot_api_key = self.settings["riot_api_key"]
        summoner_name = self.settings["default_summoner"]
        def_region = self.settings["default_region"]

        if len(riot_api_key) == 0:
            log.error("Missing riot API key in settings.")
            return False

        # https://developer.riotgames.com/docs/lol#_routing-values
        region_list = [
            "br1",
            "eun1",
            "euw1",
            "jp1",
            "kr",
            "la1",
            "la2",
            "na1",
            "oc1",
            "tr1",
            "ru",
        ]

        if message:
            summoner_name = message.split()[0]
            try:
                region = message.split()[1].lower()
            except IndexError:
                region = def_region.lower()

            if region not in region_list:
                bot.whisper(
                    source,
                    f"Region is not valid. Please enter a valid region, region is optional and the default region is {def_region.upper()}",
                )
                return False
        else:
            region = def_region.lower()

        if len(summoner_name) == 0 or len(region) == 0:
            return False

        try:
            lw = LolWatcher(riot_api_key)

            summoner = lw.summoner.by_name(region, summoner_name)
            summoner_id = str(summoner["id"])
            summoner_name = summoner["name"]

        except ApiError as e:
            log.exception("babyrage")
            if e.response.status_code == 429:
                bot.say(f"Too many requests. Try again in {e.response.headers['Retry-After']} seconds")
            elif e.response.status_code == 404:
                bot.say("The summoner not found. Use a valid summoner name (remove spaces) and region FailFish")
            return False

        try:
            summoner_league = lw.league.by_summoner(region, summoner_id)

            if len(summoner_league) == 0:
                bot.say(f"The Summoner {summoner_name} on region {region.upper()} is currently UNRANKED.. FeelsBadMan")
                return False

            tier = summoner_league[0]["tier"]
            rank = summoner_league[0]["rank"]
            league_points = summoner_league[0]["leaguePoints"]

            bot.say(
                f"The Summoner {summoner_name} on region {region.upper()} is currently in {tier} {rank} with {league_points} LP 4Head"
            )
        except ApiError as e:
            log.exception("babyrage")
            if e.response.status_code == 429:
                bot.say(f"Too many requests. Try again in {e.response.headers['Retry-After']} seconds")
            elif e.response.status_code == 404:
                bot.say(f"The Summoner {summoner_name} on region {region.upper()} is currently UNRANKED.. FeelsBadMan")
            else:
                bot.say("Trouble fetching summoner rank.. Kappa Try again later!")
            return False
