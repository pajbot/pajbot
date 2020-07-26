import logging

import requests

from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class WolframModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Wolfram Alpha Query"
    DESCRIPTION = "Lets users ask questions and have the Wolfram Alpha API answer. Requires Wolfram API token in the module settings"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="level",
            label="Level required to use the command (make sure people don't abuse this command)",
            type="number",
            required=True,
            placeholder="",
            default=250,
            constraints={"min_value": 100, "max_value": 2000},
        ),
        ModuleSetting(
            key="global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=15,
            constraints={"min_value": 0, "max_value": 240},
        ),
        ModuleSetting(
            key="user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=30,
            constraints={"min_value": 0, "max_value": 240},
        ),
        ModuleSetting(
            key="wolfram_appid",
            label="Wolfram AppID required for queries | Get an AppID here: http://developer.wolframalpha.com/portal/myapps",
            type="text",
            required=True,
            placeholder="ABCDEF-GHIJKLMNOP",
            default="",
        ),
        ModuleSetting(
            key="wolfram_ip",
            label="IP address used for location-based queries",
            type="text",
            required=True,
            placeholder="81.258.583.201",
            default="",
        ),
        ModuleSetting(
            key="wolfram_location",
            label="Location used for location-based queries (Only works if Wolfram IP is empty) | More information available here: https://products.wolframalpha.com/api/documentation/#semantic-location",
            type="text",
            required=True,
            placeholder="Sweden",
            default="",
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)

        if bot:
            self.app_id = bot.config["main"].get("wolfram", None)
            self.config_ip = bot.config["main"].get("wolfram_ip", None)
            self.config_location = bot.config["main"].get("wolfram_location", None)

    def query(self, bot, source, message, event, args):
        if self.settings["wolfram_appid"] != "":
            self.app_id = self.settings["wolfram_appid"]
        if self.settings["wolfram_ip"] != "":
            self.config_ip = self.settings["wolfram_ip"]
        if self.settings["wolfram_location"] != "":
            self.config_location = self.settings["wolfram_location"]

        if not self.app_id:
            streamer = bot.streamer_display
            bot.say(f"{streamer}, The Wolfram module is enabled, but no AppID has been configured.")
            return False

        try:
            log.debug('Querying wolfram for input "%s"', message)

            query_parameters = {
                "appid": self.app_id,
                "input": message,
                "output": "json",
                "format": "plaintext",
                "reinterpret": "true",
                "units": "metric",
            }

            # location-specific/IP-specific results, such as "current time", etc.
            if self.config_ip is not None:
                query_parameters["ip"] = self.config_ip
            elif self.config_location is not None:
                query_parameters["location"] = self.config_location

            res = requests.get(
                "https://api.wolframalpha.com/v2/query", params=query_parameters, headers={"User-Agent": bot.user_agent}
            )
            answer = res.json()["queryresult"]

            base_reply = f"{source}, "

            is_error = answer["error"]
            is_success = answer["success"]
            log.debug("Result status: error: %s, success: %s", is_error, is_success)

            if is_error:
                reply = base_reply + "your query errored FeelsBadMan"
                bot.send_message_to_user(source, reply, event, method="reply")
                return False

            if not is_success:
                log.debug(answer)
                reply = base_reply + "Wolfram|Alpha didn't understand your query FeelsBadMan"
                didyoumeans = answer.get("didyoumeans", None)
                if didyoumeans is not None and len(didyoumeans) > 0:
                    reply += " Did you mean: "

                    if isinstance(didyoumeans, dict):
                        # When there is only one "didyoumean", Wolfram|Alpha returns
                        # a single object under the "didyoumeans" key, so we convert it
                        # into a single-element list.
                        didyoumeans = [didyoumeans]
                    reply += " | ".join(list(map(lambda x: x.get("val", None), didyoumeans)))
                log.debug(reply)
                bot.send_message_to_user(source, reply, event, method="reply")
                return False

            # pods and subpods explanation: https://products.wolframalpha.com/api/documentation/#subpod-states
            def stringify_subpod(subpod):
                lines = subpod["plaintext"].splitlines()
                lines = map(str.strip, lines)  # strip all lines
                return "; ".join(lines)

            def stringify_pod(pod):
                subpods = pod["subpods"]
                stringified_subpods = map(stringify_subpod, subpods)
                all_subpods = " / ".join(stringified_subpods)
                return f"{pod['title']}: {all_subpods}"

            # find the right pods to print to chat.
            # if there is an "Input" and "Result" pod, choose those two.

            # If there are no "Input" and "Result" pods,
            # (no direct result to the query - general knowledge was
            # requested) - we concat all pods until we reach the 500 characters
            # char limit.

            # The "Input" pod is only included if its title is exactly "Input".
            # (so we print the "Input Interpretation", but dont echo the "Input"
            # as-is if it was understood by WolframAlpha as-is.

            pods = answer["pods"]

            input_pod = next((pod for pod in pods if pod["id"].lower() == "input"), None)
            result_pod = next((pod for pod in pods if pod["id"].lower() == "result"), None)
            is_direct_input_pod = input_pod is not None and input_pod["title"].lower() == "input"

            if input_pod is not None and result_pod is not None:
                selected_pods = [input_pod, result_pod]
            else:
                selected_pods = pods.copy()

            if is_direct_input_pod:
                selected_pods.remove(input_pod)

            stringified_pods = map(stringify_pod, selected_pods)
            complete_answer = " ❚ ".join(stringified_pods)
            reply = base_reply + complete_answer

            reply = (reply[:499] + "…") if len(reply) > 500 else reply

            bot.send_message_to_user(source, reply, event, method="reply")

        except:
            log.exception("wolfram query errored")

    def load_commands(self, **options):
        self.commands["query"] = Command.raw_command(
            self.query,
            delay_all=self.settings["global_cd"],
            delay_user=self.settings["user_cd"],
            level=self.settings["level"],
            description="Ask Wolfram Alpha a question",
            command="query",
            examples=[
                CommandExample(
                    None,
                    "Ask Wolfram Alpha how big the moon is",
                    chat="user:!query how big is the moon?\n"
                    "bot:pajlada, Input interpretation: Moon | average radius ❚ Result: 1737.4 km (kilometers)",
                    description="",
                ).parse(),
                CommandExample(
                    None,
                    "Ask Wolfram Alpha what time it is, relative to the location set in the module",
                    chat="user:!query what is the time?\n"
                    "bot:pajlada, Input interpretation: current time ❚ Result: 2:22:02 pm CEST | Saturday, July 13, 2019",
                    description="",
                ).parse(),
                CommandExample(
                    None,
                    "Ask Wolfram Alpha where your car is",
                    chat="user:!query where is my car\n"
                    "bot:TETYYS, Input interpretation: Where is my car (truck, ...)? ❚ Result: Not sure, but wherever you find it, that's where it is.",
                    description="",
                ).parse(),
            ],
        )
        self.commands["wolfram"] = self.commands["query"]
        self.commands["wolframquery"] = self.commands["query"]
