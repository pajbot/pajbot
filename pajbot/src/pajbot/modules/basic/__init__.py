import logging

from pajbot.modules import BaseModule
from pajbot.modules.base import ModuleType

log = logging.getLogger(__name__)


class BasicCommandsModule(BaseModule):
    ID = "basiccommands-group"
    NAME = "Basic Commands"
    DESCRIPTION = "A collection of basic commands"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
