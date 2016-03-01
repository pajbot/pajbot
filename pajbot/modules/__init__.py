from pajbot.modules.base import BaseModule, ModuleSetting

from pajbot.modules.ascii import AsciiProtectionModule
from pajbot.modules.banphrase import BanphraseModule
from pajbot.modules.bingo import BingoModule
from pajbot.modules.deck import DeckModule
from pajbot.modules.duel import DuelModule
from pajbot.modules.dummy import DummyModule
from pajbot.modules.eightball import EightBallModule
from pajbot.modules.emotecombo import EmoteComboModule
from pajbot.modules.emotesonscreen import EmotesOnScreenModule
from pajbot.modules.followage import FollowAgeModule
from pajbot.modules.givepoints import GivePointsModule
from pajbot.modules.hsbet import HSBetModule
from pajbot.modules.lastfm import LastfmModule
from pajbot.modules.leaguerank import LeagueRankModule
from pajbot.modules.linefarming import LineFarmingModule
from pajbot.modules.linkchecker import LinkCheckerModule, WhitelistedLink, BlacklistedLink
from pajbot.modules.linktracker import LinkTrackerModule, LinkTrackerLink
from pajbot.modules.math import MathModule
from pajbot.modules.maxmsglength import MaxMsgLengthModule
from pajbot.modules.paidsubmode import PaidSubmodeModule
from pajbot.modules.paidtimeout import PaidTimeoutModule, PaidTimeoutDiscountModule
from pajbot.modules.pointlottery import PointLotteryModule
from pajbot.modules.predict import PredictModule
from pajbot.modules.pyramid import PyramidModule
from pajbot.modules.quest import QuestModule
from pajbot.modules.quests.gettimedout import GetTimedOutQuestModule
from pajbot.modules.quests.typeemote import TypeEmoteQuestModule
from pajbot.modules.quests.winduelpoints import WinDuelPointsQuestModule
from pajbot.modules.quests.winraffle import WinRaffleQuestModule
from pajbot.modules.raffle import RaffleModule, MultiRaffleModule
from pajbot.modules.roulette import RouletteModule
from pajbot.modules.subalert import SubAlertModule
from pajbot.modules.tokencommands.playsound import PlaySoundTokenCommandModule
from pajbot.modules.tokencommands.showemote import ShowEmoteTokenCommandModule
from pajbot.modules.vanish import VanishModule
from pajbot.modules.warning import WarningModule

available_modules = [
        AsciiProtectionModule,
        BanphraseModule,
        BingoModule,
        DeckModule,
        DuelModule,
        DummyModule,
        EightBallModule,
        EmoteComboModule,
        EmotesOnScreenModule,
        FollowAgeModule,
        GetTimedOutQuestModule,
        GivePointsModule,
        HSBetModule,
        LastfmModule,
        LeagueRankModule,
        LineFarmingModule,
        LinkCheckerModule,
        LinkTrackerModule,
        MathModule,
        MaxMsgLengthModule,
        MultiRaffleModule,
        PaidSubmodeModule,
        PaidTimeoutDiscountModule,
        PaidTimeoutModule,
        PlaySoundTokenCommandModule,
        PointLotteryModule,
        PredictModule,
        PyramidModule,
        QuestModule,
        RaffleModule,
        RouletteModule,
        ShowEmoteTokenCommandModule,
        SubAlertModule,
        TypeEmoteQuestModule,
        VanishModule,
        WarningModule,
        WinDuelPointsQuestModule,
        WinRaffleQuestModule,
        ]
