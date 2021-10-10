from typing import Any, Dict, List

import pajbot.web.utils
from pajbot.utils import find

from flask import render_template


def init(app):
    def get_commands_list() -> List[Dict[str, Any]]:
        return pajbot.web.utils.get_cached_commands()

    @app.route("/commands")
    def commands() -> str:
        custom_commands = []
        point_commands = []
        moderator_commands = []

        bot_commands_list = get_commands_list()

        for command in bot_commands_list:
            if command["level"] > 100 or command["mod_only"]:
                moderator_commands.append(command)
            elif command["cost"] > 0:
                point_commands.append(command)
            else:
                custom_commands.append(command)

        return render_template(
            "commands.html",
            custom_commands=sorted(custom_commands, key=lambda f: f["aliases"]),
            point_commands=sorted(point_commands, key=lambda a: (a["cost"], a["aliases"])),
            moderator_commands=sorted(
                moderator_commands, key=lambda c: (c["level"] if c["mod_only"] is False else 500, c["aliases"])
            ),
        )

    @app.route("/commands/<raw_command_string>")
    def command_detailed(raw_command_string):
        command_string_parts = raw_command_string.split("-")
        command_string = command_string_parts[0]
        command_id = None
        try:
            command_id = int(command_string)
        except ValueError:
            pass

        bot_commands_list = get_commands_list()

        if command_id is not None:
            command = find(lambda c: c["id"] == command_id, bot_commands_list)
        else:
            command = find(lambda c: c["resolve_string"] == command_string, bot_commands_list)

        if command is None:
            # XXX: Is it proper to have it return a 404 code as well?
            return render_template("command_404.html")

        examples = command["examples"]

        return render_template("command_detailed.html", command=command, examples=examples)
