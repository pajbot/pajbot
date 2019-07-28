import logging
import operator

from pajbot.utils import find

log = logging.getLogger("pajbot")


class HandlerManager:
    handlers = {}

    @staticmethod
    def init_handlers():
        HandlerManager.handlers = {}

        # on_pubmsg(source, message)
        HandlerManager.create_handler("on_pubmsg")

        # on_message(source, message, emote_instances, emote_counts, whisper, urls, msg_id, event)
        HandlerManager.create_handler("on_message")

        # on_usernotice(source, message, tags)
        HandlerManager.create_handler("on_usernotice")

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
    def create_handler(event):
        """ Create an empty list for the given event """
        HandlerManager.handlers[event] = []

    @staticmethod
    def add_handler(event, method, priority=0):
        try:
            HandlerManager.handlers[event].append((method, priority))
            HandlerManager.handlers[event].sort(key=operator.itemgetter(1), reverse=True)
        except KeyError:
            # No handlers for this event found
            log.error("add_handler No handler for {} found.".format(event))

    @staticmethod
    def method_matches(h, method):
        return h[0] == method

    @staticmethod
    def remove_handler(event, method):
        handler = None
        try:
            handler = find(lambda h: HandlerManager.method_matches(h, method), HandlerManager.handlers[event])
            if handler is not None:
                HandlerManager.handlers[event].remove(handler)
        except KeyError:
            # No handlers for this event found
            log.error("remove_handler No handler for {} found.".format(event))

    @staticmethod
    def trigger(event_name, stop_on_false=True, *args, **kwargs):
        if event_name not in HandlerManager.handlers:
            log.error("No handler set for event {}".format(event_name))
            return False

        for handler, _ in HandlerManager.handlers[event_name]:
            res = None
            try:
                res = handler(*args, **kwargs)
            except:
                log.exception("Unhandled exception from {} in {}".format(handler, event_name))

            if res is False and stop_on_false is True:
                # Abort if handler returns false and stop_on_false is enabled
                return False

        return True
