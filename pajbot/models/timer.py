"""
Timers should be creatable from web UI
Timers should be editable from web UI
Timers should be removable from web UI
Timers should run after being created
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, TypedDict

import json
import logging

from pajbot.managers.db import Base, DBManager
from pajbot.models.action import ActionParser, BaseAction
from pajbot.models.user import User
from pajbot.utils import find

from sqlalchemy import Boolean, Integer, Text, event
from sqlalchemy.orm import Mapped, QueryContext, mapped_column

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger("pajbot")


class TimerOptions(TypedDict):
    name: str
    interval_online: int
    interval_offline: int
    action: Dict[str, Any]


class Timer(Base):
    __tablename__ = "timer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str]
    action_json: Mapped[str] = mapped_column("action", Text)
    interval_online: Mapped[int]
    interval_offline: Mapped[int]
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    def __init__(self) -> None:
        self.name = "??"
        self.action: Optional[BaseAction] = None
        self.action_json = "{}"
        self.interval_online = 5
        self.interval_offline = 30
        self.enabled = True

        self.refresh_tts()

    def set(self, options: TimerOptions) -> None:
        self.name = options.get("name", self.name)
        log.debug(options)
        if "action" in options:
            log.info("new action!")
            self.action_json = json.dumps(options["action"])
            self.action = ActionParser.parse(self.action_json)
        self.interval_online = options.get("interval_online", self.interval_online)
        self.interval_offline = options.get("interval_offline", self.interval_offline)

    def refresh_tts(self) -> None:
        self.time_to_send_online = self.interval_online
        self.time_to_send_offline = self.interval_offline

    def refresh_action(self) -> None:
        self.action = ActionParser.parse(self.action_json)

    def run(self, bot: Bot) -> None:
        if self.action is None:
            log.warning(f"Timer action is None, invalid action. Timer ID: {self.id}")
            return

        dummy_user = User()
        self.action.run(bot, dummy_user, "")


@event.listens_for(Timer, "load")
def on_timer_load(target: Timer, context: QueryContext) -> None:
    log.info("REFRESHING TIMER SINCE IT UPDATED")
    target.action = ActionParser.parse(target.action_json)
    target.refresh_tts()


class TimerManager:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

        self.timers: List[Timer] = []
        self.online_timers: List[Timer] = []
        self.offline_timers: List[Timer] = []

        self.bot.execute_every(60, self.tick)

        if self.bot:
            self.bot.socket_manager.add_handler("timer.update", self.on_timer_update)
            self.bot.socket_manager.add_handler("timer.remove", self.on_timer_remove)

    def on_timer_update(self, data: Dict[str, Any]) -> None:
        try:
            timer_id = int(data["id"])
        except (KeyError, ValueError):
            log.warning("No timer ID found in on_timer_update")
            return

        updated_timer = find(lambda timer: timer.id == timer_id, self.timers)
        if updated_timer:
            with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                db_session.add(updated_timer)
                db_session.refresh(updated_timer)
                updated_timer.refresh_action()
                db_session.expunge(updated_timer)
        else:
            with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                updated_timer = db_session.query(Timer).filter_by(id=timer_id).one_or_none()

        # Add the updated timer to the timer lists if required
        if updated_timer:
            if updated_timer not in self.timers:
                self.timers.append(updated_timer)

            if updated_timer not in self.online_timers:
                if updated_timer.interval_online > 0:
                    self.online_timers.append(updated_timer)
                    updated_timer.refresh_tts()

            if updated_timer not in self.offline_timers:
                if updated_timer.interval_offline > 0:
                    self.offline_timers.append(updated_timer)
                    updated_timer.refresh_tts()

        for timer in self.online_timers:
            if timer.enabled is False or timer.interval_online <= 0:
                self.online_timers.remove(timer)

        for timer in self.offline_timers:
            if timer.enabled is False or timer.interval_offline <= 0:
                self.offline_timers.remove(timer)

    def on_timer_remove(self, data: Dict[str, Any]) -> None:
        try:
            timer_id = int(data["id"])
        except (KeyError, ValueError):
            log.warning("No timer ID found in on_timer_update")
            return

        removed_timer = find(lambda timer: timer.id == timer_id, self.timers)
        if removed_timer:
            if removed_timer in self.timers:
                self.timers.remove(removed_timer)
            if removed_timer in self.online_timers:
                self.online_timers.remove(removed_timer)
            if removed_timer in self.offline_timers:
                self.offline_timers.remove(removed_timer)

    def tick(self) -> None:
        if self.bot.is_online:
            for active_timer in self.online_timers:
                active_timer.time_to_send_online -= 1

            timer = find(lambda timer: timer.time_to_send_online <= 0, self.online_timers)
            if timer:
                timer.run(self.bot)
                timer.time_to_send_online = timer.interval_online
                self.online_timers.remove(timer)
                self.online_timers.append(timer)
        else:
            for active_timer in self.offline_timers:
                active_timer.time_to_send_offline -= 1

            timer = find(lambda timer: timer.time_to_send_offline <= 0, self.offline_timers)
            if timer:
                timer.run(self.bot)
                timer.time_to_send_offline = timer.interval_offline
                self.offline_timers.remove(timer)
                self.offline_timers.append(timer)

    def redistribute_timers(self) -> None:
        for x in range(0, len(self.offline_timers)):
            timer = self.offline_timers[x]
            timer.time_to_send_offline = int(timer.interval_offline * ((x + 1) / len(self.offline_timers)))

        for x in range(0, len(self.online_timers)):
            timer = self.online_timers[x]
            timer.time_to_send_online = int(timer.interval_online * ((x + 1) / len(self.online_timers)))

    def load(self) -> TimerManager:
        self.timers = []
        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            self.timers = (
                db_session.query(Timer).order_by(Timer.interval_online, Timer.interval_offline, Timer.name).all()
            )
            db_session.expunge_all()

        self.online_timers = [timer for timer in self.timers if timer.interval_online > 0 and timer.enabled]
        self.offline_timers = [timer for timer in self.timers if timer.interval_offline > 0 and timer.enabled]

        self.redistribute_timers()

        log.info(
            f"Loaded {len(self.timers)} timers ({len(self.online_timers)} online/{len(self.offline_timers)} offline)"
        )
        return self
