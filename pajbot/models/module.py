from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

import json
import logging

from pajbot.managers.db import Base, DBManager
from pajbot.utils import find

import sqlalchemy
from sqlalchemy import BOOLEAN, TEXT, Column

if TYPE_CHECKING:
    from pajbot.bot import Bot
    from pajbot.models.sock import HandlerParam, SocketManager
    from pajbot.modules import BaseModule

log = logging.getLogger("pajbot")


class Module(Base):
    __tablename__ = "module"

    id = Column(TEXT, primary_key=True)
    enabled = Column(BOOLEAN, nullable=False, default=False, server_default=sqlalchemy.sql.expression.false())
    settings = Column(TEXT, nullable=True, default=None, server_default=sqlalchemy.sql.expression.null())

    def __init__(self, module_id: str, **options: Any) -> None:
        self.id = module_id
        self.enabled = options.get("enabled", False)
        self.settings = None


class ModuleManager:
    def __init__(self, socket_manager: Optional[SocketManager], bot: Optional[Bot] = None) -> None:
        # List of all enabled modules
        self.modules: List[BaseModule] = []

        # List of all available modules, both enabled and disabled
        self.all_modules: List[BaseModule] = []

        self.bot = bot

        if socket_manager:
            socket_manager.add_handler("module.update", self.on_module_update)

    def get_module(self, module_id: str) -> Optional[BaseModule]:
        return find(lambda m: m.ID == module_id, self.all_modules)

    def on_module_update(self, data: HandlerParam) -> None:
        new_state = data.get("new_state", None)
        if new_state is True:
            self.enable_module(data["id"])
        elif new_state is False:
            self.disable_module(data["id"])
        else:
            module = self.get_module(data["id"])

            if module:
                module.load()
                module.on_loaded()

    def enable_module(self, module_id: str) -> bool:
        module = self.get_module(module_id)
        if module is None:
            log.error(f"No module with the ID {module_id} found.")
            return False

        module.load()
        module.on_loaded()

        module.enable(self.bot)

        if module in self.modules:
            log.error("Module %s is already in the list of enabled modules pajaW", module_id)
            return False

        self.modules.append(module)

        return True

    def disable_module(self, module_id: str) -> bool:
        module = self.get_module(module_id)
        if not module:
            log.error(f"No module with the ID {module_id} found.")
            return False

        module.disable(self.bot)

        if module not in self.modules:
            log.error(f"Module {module_id} is not in the list of enabled modules pajaW")
            return False

        self.modules.remove(module)

        return True

    def load(self, do_reload: bool = True) -> ModuleManager:
        """Load module classes"""

        from pajbot.modules import available_modules

        self.all_modules = [module(self.bot) for module in available_modules]

        with DBManager.create_session_scope() as db_session:
            # Make sure there's a row in the DB for each module that's available
            db_modules = db_session.query(Module).all()
            for module in self.all_modules:
                mod = find(lambda db_module: db_module.id == module.ID, db_modules)
                if mod is None:
                    log.info(f"Creating row in DB for module {module.ID}")
                    mod = Module(module.ID, enabled=module.ENABLED_DEFAULT)
                    db_session.add(mod)

        if do_reload is True:
            # Mark modules as enabled/disabled if their state has changed
            self.reload()

        return self

    def _disable_all_modules(self) -> None:
        for module in self.modules:
            module.disable(self.bot)

    def _load_enabled_modules(self) -> None:
        """Load modules from the database and put them into the modules list"""
        with DBManager.create_session_scope() as db_session:
            for enabled_module in db_session.query(Module).filter_by(enabled=True):
                module = self.get_module(enabled_module.id)
                if module is not None:
                    options = {}
                    if enabled_module.settings is not None:
                        try:
                            options["settings"] = json.loads(enabled_module.settings)
                        except ValueError:
                            log.warning("Invalid JSON")

                    self.modules.append(module.load(**options))
                    module.on_loaded()
                    module.enable(self.bot)

    def _disable_orphan_modules(self) -> None:
        to_be_removed: List[BaseModule] = []
        self.modules.sort(key=lambda m: 1 if m.PARENT_MODULE is not None else 0)
        for module in self.modules:
            if module.PARENT_MODULE is None:
                module.submodules = []
            else:
                parent = find(lambda m: m.__class__ == module.PARENT_MODULE, self.modules)
                if parent is not None:
                    parent.submodules.append(module)
                    module.parent_module = parent
                else:
                    # log.warning('Missing parent for module {}, disabling it.'.format(module.NAME))
                    module.parent_module = None
                    to_be_removed.append(module)

        for module in to_be_removed:
            module.disable(self.bot)
            self.modules.remove(module)

    def reload(self) -> None:
        # TODO: Make disable/enable better, so we don't need to disable modules
        # that we're just going to enable again further down below.
        self._disable_all_modules()

        self.modules.clear()

        self._load_enabled_modules()

        self._disable_orphan_modules()

        # Perform a last on_loaded call on each module.
        # This is used for things that require submodules to be loaded properly
        # i.e. the quest system
        for module in self.modules:
            module.on_loaded()

    def __getitem__(self, module_id: str) -> Optional[BaseModule]:
        for enabled_module in self.modules:
            if enabled_module.ID == module_id:
                return enabled_module

        return None

    def __contains__(self, module_id: str) -> bool:
        """We override the contains operator for the ModuleManager.
        This allows us to use the following syntax to check if a module is enabled:
        if 'duel' in module_manager:
        """

        for enabled_module in self.modules:
            if enabled_module.ID == module_id:
                return True

        return False
