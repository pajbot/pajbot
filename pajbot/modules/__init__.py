from pajbot.modules.base import BaseModule
from pajbot.modules.base import ModuleSetting
from pajbot.modules.base import ModuleType

from pajbot.modules.ascii import AsciiProtectionModule
from pajbot.modules.banphrase import BanphraseModule
from pajbot.modules.basic import BasicCommandsModule
from pajbot.modules.basic.ab import AbCommandModule
from pajbot.modules.basic.admincommands import AdminCommandsModule
from pajbot.modules.basic.bttvemotes import BTTVEmotesModule
from pajbot.modules.basic.checkmod import CheckModModule
from pajbot.modules.basic.dbmanage import DBManageModule
from pajbot.modules.basic.debug import DebugModule
from pajbot.modules.basic.ffzemotes import FFZEmotesModule
from pajbot.modules.basic.ignore import IgnoreModule
from pajbot.modules.basic.permaban import PermabanModule
from pajbot.modules.basic.pointsreset import PointsResetModule
from pajbot.modules.bingo import BingoModule
from pajbot.modules.blackjack import BlackjackModule
from pajbot.modules.chatters import ChattersModule
from pajbot.modules.deck import DeckModule
from pajbot.modules.dubtrack import DubtrackModule
from pajbot.modules.duel import DuelModule
from pajbot.modules.dummy import DummyModule
from pajbot.modules.eightball import EightBallModule
from pajbot.modules.emotecombo import EmoteComboModule
from pajbot.modules.emotesonscreen import EmotesOnScreenModule
from pajbot.modules.followage import FollowAgeModule
from pajbot.modules.givepoints import GivePointsModule
from pajbot.modules.highlight import HighlightModule
from pajbot.modules.hsbet import HSBetModule
from pajbot.modules.lastfm import LastfmModule
from pajbot.modules.leaguerank import LeagueRankModule
from pajbot.modules.linefarming import LineFarmingModule
from pajbot.modules.linkchecker import BlacklistedLink
from pajbot.modules.linkchecker import LinkCheckerModule
from pajbot.modules.linkchecker import WhitelistedLink
from pajbot.modules.linktracker import LinkTrackerLink
from pajbot.modules.linktracker import LinkTrackerModule
from pajbot.modules.math import MathModule
from pajbot.modules.maxmsglength import MaxMsgLengthModule
from pajbot.modules.paidsubmode import PaidSubmodeModule
from pajbot.modules.paidtimeout import PaidTimeoutDiscountModule
from pajbot.modules.paidtimeout import PaidTimeoutModule
from pajbot.modules.paiduntimeout import PaidUntimeoutModule
from pajbot.modules.personaluptime import PersonalUptimeModule
from pajbot.modules.pleblist import PleblistModule
from pajbot.modules.pointlottery import PointLotteryModule
from pajbot.modules.predict import PredictModule
from pajbot.modules.pyramid import PyramidModule
from pajbot.modules.quest import QuestModule
from pajbot.modules.quests.gettimedout import GetTimedOutQuestModule
from pajbot.modules.quests.typeemote import TypeEmoteQuestModule
from pajbot.modules.quests.typememessage import TypeMeMessageQuestModule
from pajbot.modules.quests.winduelpoints import WinDuelPointsQuestModule
from pajbot.modules.quests.winduels import WinDuelsQuestModule
from pajbot.modules.quests.winhsbetpoints import WinHsBetPointsQuestModule
from pajbot.modules.quests.winhsbetwins import WinHsBetWinsQuestModule
from pajbot.modules.quests.winraffle import WinRaffleQuestModule
from pajbot.modules.raffle import RaffleModule
from pajbot.modules.roulette import RouletteModule
from pajbot.modules.subalert import SubAlertModule
from pajbot.modules.tokencommands.playsound import PlaySoundTokenCommandModule
from pajbot.modules.tokencommands.showemote import ShowEmoteTokenCommandModule
from pajbot.modules.top import TopModule
from pajbot.modules.trivia import TriviaModule
from pajbot.modules.vanish import VanishModule
from pajbot.modules.warning import WarningModule

available_modules = [
        AbCommandModule,
        AdminCommandsModule,
        AsciiProtectionModule,
        BTTVEmotesModule,
        BanphraseModule,
        BasicCommandsModule,
        BingoModule,
        ChattersModule,
        CheckModModule,
        DBManageModule,
        DebugModule,
        DeckModule,
        DubtrackModule,
        DuelModule,
        DummyModule,
        EightBallModule,
        EmoteComboModule,
        EmotesOnScreenModule,
        FFZEmotesModule,
        FollowAgeModule,
        GetTimedOutQuestModule,
        GivePointsModule,
        HSBetModule,
        HighlightModule,
        IgnoreModule,
        LastfmModule,
        LeagueRankModule,
        LineFarmingModule,
        LinkCheckerModule,
        LinkTrackerModule,
        MathModule,
        MaxMsgLengthModule,
        PaidSubmodeModule,
        PaidTimeoutDiscountModule,
        PaidTimeoutModule,
        PaidUntimeoutModule,
        PermabanModule,
        PersonalUptimeModule,
        PlaySoundTokenCommandModule,
        PleblistModule,
        PointLotteryModule,
        PointsResetModule,
        PredictModule,
        PyramidModule,
        QuestModule,
        RaffleModule,
        RouletteModule,
        ShowEmoteTokenCommandModule,
        SubAlertModule,
        TopModule,
        TriviaModule,
        TypeEmoteQuestModule,
        TypeMeMessageQuestModule,
        VanishModule,
        WarningModule,
        WinDuelPointsQuestModule,
        WinDuelsQuestModule,
        WinHsBetPointsQuestModule,
        WinHsBetWinsQuestModule,
        WinRaffleQuestModule,
        ]
