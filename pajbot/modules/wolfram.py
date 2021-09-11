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
    DESCRIPTION = "Lets users ask questions and have the Wolfram Alpha API answer. Requires Wolfram API token in the bot config file"
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
            key="wolfram_ip",
            label="Tell Wolfram we have a different IP",
            type="text",
            required=True,
            placeholder="81.258.583.201",
            default="",
        ),
        ModuleSetting(
            key="wolfram_location",
            label="Tell Wolfram we have a different location (Only works if Wolfram IP is empty)",
            type="text",
            required=True,
            placeholder="Sweden",
            default="",
        ),
        ModuleSetting(
            key="response_method",
            label="Method of response to command usage",
            type="options",
            required=True,
            default="say",
            options=["say", "whisper", "reply"],
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)

        if bot:
            self.app_id = bot.config["main"].get("wolfram", None)
            self.config_ip = bot.config["main"].get("wolfram_ip", None)
            self.config_location = bot.config["main"].get("wolfram_location", None)

    def query(self, bot, source, message, event, args):
        ip = self.settings["wolfram_ip"]
        location = self.settings["wolfram_location"]

        if self.config_ip:
            # Override module settings "ip" with what's set in the config file
            ip = self.config_ip
        if self.config_location:
            # Override module settings "location" with what's set in the config file
            location = self.config_location

        if not self.app_id:
            # XXX: Possibly notify user of misconfigured bot?
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
            if ip is not None:
                query_parameters["ip"] = ip
            elif location is not None:
                query_parameters["location"] = location

            res = requests.get(
                "https://api.wolframalpha.com/v2/query", params=query_parameters, headers={"User-Agent": bot.user_agent}
            )
            answer = res.json()["queryresult"]

            is_error = answer["error"]
            is_success = answer["success"]
            log.debug("Result status: error: %s, success: %s", is_error, is_success)

            if is_error:
                bot.send_message_to_user(
                    source, "Your query errored FeelsBadMan", event, method=self.settings["response_method"]
                )
                return False

            if not is_success:
                log.debug(answer)
                reply = "Wolfram|Alpha didn't understand your query FeelsBadMan"
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
                bot.send_message_to_user(source, reply, event, method=self.settings["response_method"])
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

            reply = (complete_answer[:499] + "…") if len(complete_answer) > 500 else complete_answer

            bot.send_message_to_user(source, reply, event, method=self.settings["response_method"])

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
            can_execute_with_whisper=(self.settings["response_method"] == "reply"),
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
