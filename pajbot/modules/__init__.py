from pajbot.modules.base import BaseModule, ModuleSetting
from pajbot.modules.dummy import DummyModule
from pajbot.modules.duel import DuelModule
from pajbot.modules.predict import PredictModule
from pajbot.modules.deck import DeckModule
from pajbot.modules.followage import FollowAgeModule
from pajbot.modules.math import MathModule
from pajbot.modules.maxmsglength import MaxMsgLengthModule

available_modules = [
        DummyModule,
        DuelModule,
        PredictModule,
        DeckModule,
        FollowAgeModule,
        MathModule,
        MaxMsgLengthModule
        ]
