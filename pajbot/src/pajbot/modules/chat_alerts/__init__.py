import logging

from pajbot.modules import BaseModule
from pajbot.modules.base import ModuleType

log = logging.getLogger(__name__)


class ChatAlertModule(BaseModule):
    ID = "chatalerts-group"
    NAME = "Chat Alerts"
    DESCRIPTION = "A collection of optional chat alerts to alert your chat when an event happens"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
