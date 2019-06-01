import json

from flask import render_template
from flask import request

from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.models.module import Module
from pajbot.models.module import ModuleManager
from pajbot.models.sock import SocketClientManager
from pajbot.utils import find
from pajbot.web.utils import requires_level


def init(page):
    @page.route("/modules/")
    @requires_level(500)
    def modules(**options):
        module_manager = ModuleManager(None).load(do_reload=False)
        for module in module_manager.all_modules:
            module.db_module = None
        with DBManager.create_session_scope() as db_session:
            for db_module in db_session.query(Module):
                module = find(lambda m: m.ID == db_module.id, module_manager.all_modules)
                if module:
                    module.db_module = db_module

            return render_template("admin/modules.html", modules=module_manager.all_modules)

    @page.route("/modules/edit/<module_id>", methods=["GET", "POST"])
    @requires_level(500)
    def modules_edit(module_id, **options):
        module_manager = ModuleManager(None).load(do_reload=False)
        current_module = find(lambda m: m.ID == module_id, module_manager.all_modules)

        if current_module is None:
            return render_template("admin/module_404.html"), 404

        sub_modules = []
        for module in module_manager.all_modules:
            module.db_module = None

        with DBManager.create_session_scope() as db_session:
            for db_module in db_session.query(Module):
                module = find(lambda m: m.ID == db_module.id, module_manager.all_modules)
                if module:
                    module.db_module = db_module
                    if module.PARENT_MODULE == current_module.__class__:
                        sub_modules.append(module)

            if current_module.db_module is None:
                return render_template("admin/module_404.html"), 404

            if request.method != "POST":
                settings = None
                try:
                    settings = json.loads(current_module.db_module.settings)
                except (TypeError, ValueError):
                    pass
                current_module.load(settings=settings)

                return render_template("admin/configure_module.html", module=current_module, sub_modules=sub_modules)

            form_values = {key: value for key, value in request.form.items()}
            res = current_module.parse_settings(**form_values)
            if res is False:
                return render_template("admin/module_404.html"), 404

            current_module.db_module.settings = json.dumps(res)
            db_session.commit()

            settings = None
            try:
                settings = json.loads(current_module.db_module.settings)
            except (TypeError, ValueError):
                pass
            current_module.load(settings=settings)

            payload = {"id": current_module.db_module.id}

            SocketClientManager.send("module.update", payload)

            AdminLogManager.post("Module edited", options["user"], current_module.NAME)

            return render_template("admin/configure_module.html", module=current_module, sub_modules=sub_modules)
