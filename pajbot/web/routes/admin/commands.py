import logging

import pajbot.managers
from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.models.command import Command, CommandData
from pajbot.models.module import ModuleManager
from pajbot.models.sock import SocketClientManager
from pajbot.web.utils import requires_level

from flask import abort, redirect, render_template, request, session
from flask.typing import ResponseReturnValue
from sqlalchemy.orm import joinedload

log = logging.getLogger(__name__)


def init(page) -> None:
    @page.route("/commands/")
    @requires_level(500)
    def commands(**options) -> ResponseReturnValue:
        from pajbot.models.module import ModuleManager

        bot_commands = pajbot.managers.command.CommandManager(
            socket_manager=None, module_manager=ModuleManager(None).load(), bot=None
        ).load(enabled=None)

        bot_commands_list = bot_commands.parse_for_web()
        custom_commands = []
        point_commands = []
        moderator_commands = []

        for command in bot_commands_list:
            if command.id is None:
                continue
            if command.level > 100 or command.mod_only:
                moderator_commands.append(command)
            elif command.cost > 0:
                point_commands.append(command)
            else:
                custom_commands.append(command)

        with DBManager.create_session_scope() as db_session:
            commands_data = (
                db_session.query(CommandData).options(joinedload(CommandData.user), joinedload(CommandData.user2)).all()
            )
            return render_template(
                "admin/commands.html",
                commands_data=commands_data,
                custom_commands=sorted(custom_commands, key=lambda f: f.command),
                point_commands=sorted(point_commands, key=lambda a: (a.cost, a.command)),
                moderator_commands=sorted(
                    moderator_commands, key=lambda c: (c.level if c.mod_only is False else 500, c.command)
                ),
                created=session.pop("command_created_id", None),
                edited=session.pop("command_edited_id", None),
            )

    @page.route("/commands/edit/<command_id>")
    @requires_level(500)
    def commands_edit(command_id, **options) -> ResponseReturnValue:
        with DBManager.create_session_scope() as db_session:
            command = (
                db_session.query(Command)
                .options(joinedload(Command.data).joinedload(CommandData.user))
                .filter_by(id=command_id)
                .one_or_none()
            )

            if command is None:
                return render_template("admin/command_404.html"), 404

            return render_template("admin/edit_command.html", command=command, user=options.get("user", None))

    @page.route("/commands/create", methods=["GET", "POST"])
    @requires_level(500)
    def commands_create(**options) -> ResponseReturnValue:
        session.pop("command_created_id", None)
        session.pop("command_edited_id", None)
        if request.method != "POST":
            return render_template("admin/create_command.html")

        if "aliases" not in request.form:
            abort(403)
        alias_str = request.form.get("aliases", "").replace("!", "").lower()
        delay_all = request.form.get("cd", Command.DEFAULT_CD_ALL)
        delay_user = request.form.get("usercd", Command.DEFAULT_CD_USER)
        level = request.form.get("level", Command.DEFAULT_LEVEL)
        cost = request.form.get("cost", 0)
        can_execute_with_whisper = request.form.get("whisperable", "off") == "on"
        sub_only = request.form.get("subonly", "off") == "on"
        mod_only = request.form.get("modonly", "off") == "on"
        run_through_banphrases = request.form.get("checkmsg", "off") == "on"

        try:
            delay_all = int(delay_all)
            delay_user = int(delay_user)
            level = int(level)
            cost = int(cost)
        except ValueError:
            abort(403)

        if not alias_str:
            abort(403)
        if delay_all < 0 or delay_all > 9999:
            abort(403)
        if delay_user < 0 or delay_user > 9999:
            abort(403)
        if level < 0 or level > 2000:
            abort(403)
        if cost < 0 or cost > 9999999:
            abort(403)

        user = options.get("user", None)

        if user is None:
            abort(403)

        options = {
            "delay_all": delay_all,
            "delay_user": delay_user,
            "level": level,
            "cost": cost,
            "added_by": user.id,
            "can_execute_with_whisper": can_execute_with_whisper,
            "sub_only": sub_only,
            "mod_only": mod_only,
            "run_through_banphrases": run_through_banphrases,
        }

        valid_action_types = ["say", "me", "announce", "whisper", "reply"]
        action_type = request.form.get("reply", "say").lower()
        if action_type not in valid_action_types:
            abort(403)

        response = request.form.get("response", "")
        if not response:
            abort(403)

        action = {"type": action_type, "message": response}
        options["action"] = action

        command_manager = pajbot.managers.command.CommandManager(
            socket_manager=None, module_manager=ModuleManager(None).load(), bot=None
        ).load(enabled=None)

        command_aliases_list = []

        for alias, command in command_manager.items():
            command_aliases_list.append(alias)
            if command.command and len(command.command) > 0:
                command_aliases_list.extend(command.command.split("|"))

        command_aliases = set(command_aliases_list)

        alias_str = alias_str.replace(" ", "").replace("!", "").lower()
        alias_list = alias_str.split("|")

        alias_list = [alias for alias in alias_list if len(alias) > 0]

        if not alias_list:
            return render_template("admin/create_command_fail.html")

        for alias in alias_list:
            if alias in command_aliases:
                return render_template("admin/create_command_fail.html")

        alias_str = "|".join(alias_list)

        command = Command(command=alias_str, **options)
        command.data = CommandData(command.id, **options)
        log_msg = f"The !{command.command.split('|')[0]} command has been created"
        AdminLogManager.add_entry("Command created", user, log_msg)
        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            db_session.add(command)
            db_session.add(command.data)
            db_session.commit()
            db_session.expunge(command)
            db_session.expunge(command.data)

        SocketClientManager.send("command.update", {"command_id": command.id})
        session["command_created_id"] = command.id
        return redirect("/admin/commands/", 303)
