from pajbot.modules.base import BaseModule, ModuleSetting
from pajbot.modules.dummy import DummyModule
from pajbot.modules.duel import DuelModule
from pajbot.modules.predict import PredictModule
from pajbot.modules.deck import DeckModule
from pajbot.modules.followage import FollowAgeModule
from pajbot.modules.math import MathModule
from pajbot.modules.maxmsglength import MaxMsgLengthModule
from pajbot.modules.ascii import AsciiProtectionModule
from pajbot.modules.pyramid import PyramidModule
from pajbot.modules.emotecombo import EmoteComboModule
from pajbot.modules.linktracker import LinkTrackerModule, LinkTrackerLink
from pajbot.modules.linkchecker import LinkCheckerModule, WhitelistedLink, BlacklistedLink
from pajbot.modules.lastfm import LastfmModule
from pajbot.modules.warning import WarningModule
from pajbot.modules.linefarming import LineFarmingModule
from pajbot.modules.bingo import BingoModule
from pajbot.modules.leaguerank import LeagueRankModule
from pajbot.modules.paidtimeout import PaidTimeoutModule, PaidTimeoutDiscountModule
from pajbot.modules.quest import QuestModule
from pajbot.modules.quests.gettimedout import GetTimedOutQuestModule
from pajbot.modules.quests.winraffle import WinRaffleQuestModule
from pajbot.modules.tokencommands.playsound import PlaySoundTokenCommandModule
from pajbot.modules.tokencommands.showemote import ShowEmoteTokenCommandModule
from pajbot.modules.emotesonscreen import EmotesOnScreenModule
from pajbot.modules.roulette import RouletteModule
from pajbot.modules.raffle import RaffleModule

available_modules = [
        DummyModule,
        DuelModule,
        PredictModule,
        DeckModule,
        FollowAgeModule,
        MathModule,
        MaxMsgLengthModule,
        AsciiProtectionModule,
        PyramidModule,
        EmoteComboModule,
        LinkTrackerModule,
        LinkCheckerModule,
        LastfmModule,
        WarningModule,
        LineFarmingModule,
        BingoModule,
        LeagueRankModule,
        QuestModule,
        GetTimedOutQuestModule,
        PaidTimeoutModule,
        PaidTimeoutDiscountModule,
        WinRaffleQuestModule,
        PlaySoundTokenCommandModule,
        ShowEmoteTokenCommandModule,
        EmotesOnScreenModule,
        RouletteModule,
        RaffleModule,
        ]
