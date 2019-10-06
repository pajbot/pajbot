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
            label="Default region",
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
                    chat="user:!rank\n"
                    "bot: The Summoner Moregain Freeman on region EUW is currently in PLATINUM IV with 62 LP 4Head",
                    description="Bot says broadcaster's region, League-tier, division and LP",
                ).parse(),
                CommandExample(
                    None,
                    "Check other player's rank on default region",
                    chat="user:!rank forsen\n"
                    "bot: The Summoner forsen on region EUW is currently in SILVER IV with 36 LP 4Head",
                    description="Bot says player's region, League-tier, division and LP",
                ).parse(),
                CommandExample(
                    None,
                    "Check other player's rank on another region",
                    chat="user:!rank imaqtpie na\n"
                    "bot: The Summoner Imaqtpie on region NA is currently in CHALLENGER I with 441 LP 4Head",
                    description="Bot says player's region, League-tier, division and LP. Other regions to use as arguments: euw, eune, na, oce, br, kr, las, lan, ru, tr",
                ).parse(),
            ],
        )
        self.commands["ranklol"] = self.commands["lolrank"]
        self.commands["leaguerank"] = self.commands["lolrank"]

    def league_rank(self, bot, source, message, **rest):
        try:
            from riotwatcher import RiotWatcher, LoLException
        except ImportError:
            log.error("Missing required module for League Rank module: riotwatcher")
            return False

        riot_api_key = self.settings["riot_api_key"]
        summoner_name = self.settings["default_summoner"]
        def_region = self.settings["default_region"]

        if len(riot_api_key) == 0:
            log.error("Missing riot API key in settings.")
            return False

        region_list = ["br", "eune", "euw", "kr", "lan", "las", "na", "oce", "ru", "tr"]

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
                pass
        else:
            region = def_region.lower()

        if len(summoner_name) == 0 or len(region) == 0:
            return False

        error_404 = "Game data not found"
        error_429 = "Too many requests"

        try:
            rw = RiotWatcher(riot_api_key, default_region=region)

            summoner = rw.get_summoner(name=summoner_name)
            summoner_id = str(summoner["id"])
            summoner_name = summoner["name"]

        except LoLException as e:
            if e == error_429:
                bot.say(f"Too many requests. Try again in {e.headers['Retry-After']} seconds")
                return False
            elif e == error_404:
                bot.say("The summoner not found. Use a valid summoner name (remove spaces) and region FailFish")
                return False
            else:
                log.info(f"Something unknown went wrong: {e}")
                return False

        try:
            summoner_league = rw.get_league_entry(summoner_ids=(summoner_id,))

            tier = summoner_league[summoner_id][0]["tier"]
            division = summoner_league[summoner_id][0]["entries"][0]["division"]
            league_points = summoner_league[summoner_id][0]["entries"][0]["leaguePoints"]

            bot.say(
                f"The Summoner {summoner_name} on region {region.upper()} is currently in {tier} {division} with {league_points} LP 4Head"
            )
        except LoLException as e:
            if e == error_429:
                bot.say(f"Too many requests. Try again in {e.headers['Retry-After']} seconds")
                return False
            elif e == error_404:
                bot.say(f"The Summoner {summoner_name} on region {region.upper()} is currently UNRANKED.. FeelsBadMan")
                return False
            else:
                bot.say("Trouble fetching summoner rank.. Kappa Try again later!")
                return False
