from typing import Dict, Any, Tuple, Callable, List

import logging
import operator

from pajbot.utils import find

log = logging.getLogger("pajbot")


class HandlerManager:
    """This Dict maps event name -> List of event handlers
    Event handler is a triple: (Callable event handler, priority, run_if_propagation_stopped)"""

    handlers: Dict[str, List[Tuple[Callable[..., bool], int, bool]]] = {}

    @staticmethod
    def init_handlers() -> None:
        HandlerManager.handlers = {}

        # on_pubmsg(source, message, tags)
        HandlerManager.create_handler("on_pubmsg")

        # on_message(source, message, emote_instances, emote_counts, whisper, urls, msg_id, event)
        HandlerManager.create_handler("on_message")

        # on_usernotice(source, message, tags)
        HandlerManager.create_handler("on_usernotice")

        # on_pubnotice(channel, msg_id, message)
        HandlerManager.create_handler("on_pubnotice")

        # on_commit()
        HandlerManager.create_handler("on_commit")

        # on_stream_start()
        HandlerManager.create_handler("on_stream_start")

        # on_stream_stop()
        HandlerManager.create_handler("on_stream_stop")

        # on_paid_timeout(source, victim, cost)
        HandlerManager.create_handler("on_paid_timeout")

        # on_raffle_win(winner, points)
        HandlerManager.create_handler("on_raffle_win")

        # on_multiraffle_win(winners, points_per_user)
        HandlerManager.create_handler("on_multiraffle_win")

        # on_roulette_finish(user, points)
        HandlerManager.create_handler("on_roulette_finish")

        # on_slot_machine_finish(user, points)
        HandlerManager.create_handler("on_slot_machine_finish")

        # on_bingo_win(winner, game)
        HandlerManager.create_handler("on_bingo_win")

        # on_managers_loaded()
        HandlerManager.create_handler("on_managers_loaded")

        # on_duel_complete(winner, loser, points_won, points_bet)
        HandlerManager.create_handler("on_duel_complete")

        # on_user_win_hs_bet(user, points_won)
        HandlerManager.create_handler("on_user_win_hs_bet")

        # on_user_sub(user)
        HandlerManager.create_handler("on_user_sub")

        # on_user_resub(user, num_months)
        HandlerManager.create_handler("on_user_resub")

        # on_tick()
        HandlerManager.create_handler("on_tick")

        # on_quit()
        HandlerManager.create_handler("on_quit")

    @staticmethod
    def create_handler(event: str) -> None:
        """Create an empty list for the given event"""
        HandlerManager.handlers[event] = []

    @staticmethod
    def add_handler(
        event: str, method: Callable[..., bool], priority: int = 0, run_if_propagation_stopped: bool = False
    ) -> None:
        try:
            HandlerManager.handlers[event].append((method, priority, run_if_propagation_stopped))
            HandlerManager.handlers[event].sort(key=operator.itemgetter(1), reverse=True)
        except KeyError:
            # No handlers for this event found
            log.error(f"HandlerManager.add_handler: No handler for {event} found.")

    @staticmethod
    def remove_handler(event: str, method: Callable[..., bool]) -> None:
        try:
            handler = find(lambda h: h[0] == method, HandlerManager.handlers[event])
            if handler is not None:
                HandlerManager.handlers[event].remove(handler)
        except KeyError:
            # No handlers for this event found
            log.error(f"remove_handler No handler for {event} found.")

    @staticmethod
    def trigger(event_name: str, stop_on_false: bool = True, *args: Any, **kwargs: Any) -> bool:
        if event_name not in HandlerManager.handlers:
            log.error(f"HandlerManager.trigger: No handler set for event {event_name}")
            return False

        propagation_stopped = False
        for handler, _, run_if_propagation_stopped in HandlerManager.handlers[event_name]:
            if propagation_stopped and not run_if_propagation_stopped:
                continue

            res = None
            try:
                res = handler(*args, **kwargs)
            except:
                log.exception(f"Unhandled exception from {handler} in {event_name}")

            if res is False and stop_on_false is True:
                # Abort if handler returns False and stop_on_false is enabled
                propagation_stopped = True

        return True
