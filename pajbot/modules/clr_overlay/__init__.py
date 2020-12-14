import logging

from pajbot.modules import BaseModule
from pajbot.modules.base import ModuleType

log = logging.getLogger(__name__)


class CLROverlayModule(BaseModule):
    ID = "clroverlay-group"
    NAME = "CLR Overlay"
    DESCRIPTION = "A collection of overlays that can be used in the streaming software of choice"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
