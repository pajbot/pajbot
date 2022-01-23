from typing import Dict, Optional, Union

import logging
from contextlib import contextmanager
from dataclasses import dataclass

log = logging.getLogger(__name__)


# @dataclass: https://stackoverflow.com/a/62699260/4464702 (Python 3.7 feature)
@dataclass
class Untimeout:
    pass


@dataclass
class Unban:
    pass


@dataclass
class Timeout:
    duration: int
    reason: Optional[str]
    once: bool


@dataclass
class Ban:
    reason: Optional[str]


# Type alias
ModerationAction = Union[Untimeout, Unban, Timeout, Ban]


def _combine_reasons(a: Optional[str], b: Optional[str]) -> Optional[str]:
    if a is None and b is None:
        return None

    if a is None:
        return b

    if b is None:
        return a

    return f"{a} + {b}"


class ModerationActions:
    # Maps login -> action to execute
    actions: Dict[str, ModerationAction]

    def __init__(self) -> None:
        super().__init__()
        self.actions = {}

    def add(self, login: str, action: ModerationAction) -> None:
        if login not in self.actions:
            self.actions[login] = action
            return

        existing_action = self.actions[login]

        if isinstance(action, Ban):
            if isinstance(existing_action, Ban):
                # combine the two
                self.actions[login] = Ban(reason=_combine_reasons(existing_action.reason, action.reason))
            else:
                # ban wins over lower-tier action
                self.actions[login] = action
            return

        if isinstance(action, Timeout):
            if isinstance(existing_action, Ban):
                # Existing action is higher-tier
                return

            if isinstance(existing_action, Timeout):
                # combine the two
                self.actions[login] = Timeout(
                    duration=max(action.duration, existing_action.duration),
                    reason=_combine_reasons(existing_action.reason, action.reason),
                    once=existing_action.once and action.once,
                )
            else:
                # timeout wins over lower-tier action
                self.actions[login] = action
            return

        if isinstance(action, Unban):
            if isinstance(existing_action, Ban) or isinstance(existing_action, Timeout):
                # Existing action is higher-tier
                return

            if isinstance(existing_action, Unban):
                # two unbans, nothing to combine
                pass
            else:
                # unban wins over lower-tier untimeout
                self.actions[login] = action
            return

        # we have an untimeout action
        # if the current action was higher-tier we wouldn't have to do anything
        # if the current action was also an untimeout we wouldn't have to do anything
        # there are no tiers below an untimeout
        # the case where there is no pre-existing action is already handled way at the top of this method
        # so, in essence, there is nothing to do here.

    def execute(self, bot) -> None:
        for login, action in self.actions.items():
            if isinstance(action, Ban):
                bot.ban_login(login, action.reason)
            if isinstance(action, Timeout):
                bot.timeout_login(login, action.duration, action.reason, action.once)
            if isinstance(action, Unban):
                bot.unban_login(login)
            if isinstance(action, Untimeout):
                bot.untimeout_login(login)


@contextmanager
def new_message_processing_scope(bot):
    bot.thread_locals.moderation_actions = ModerationActions()

    try:
        yield
    finally:
        mod_actions = bot.thread_locals.moderation_actions
        bot.thread_locals.moderation_actions = None
        try:
            mod_actions.execute(bot)
        except:
            log.exception("Failed to execute moderation actions after message processing scope ended")
