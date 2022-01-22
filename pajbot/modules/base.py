from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import json
import logging

from pajbot.bot import Bot
from pajbot.config import Config
from pajbot.managers.db import DBManager
from pajbot.models.module import Module
from pajbot.utils import find

log = logging.getLogger(__name__)


class ModuleSetting:
    """
    A single setting for a Module.

    Available types:
      * text - A text input
        Available constraints:
          * min_str_len
          * max_str_len
      * number - A number input (Integer)
          * min_value
          * max_value
      * boolean - A checkbox input
      * options - A select/options list
    """

    def __init__(
        self,
        key: str,
        label: str,
        type: str,
        required: bool = False,
        placeholder: str = "",
        default: Optional[Any] = None,
        constraints: Dict[str, Any] = {},
        options: List[str] = [],
    ) -> None:
        self.key = key
        self.label = label
        self.type = type
        self.required = required
        self.placeholder = placeholder
        self.default = default
        self.constraints = constraints
        self.options = options

    def validate(self, value: str) -> Tuple[bool, Any]:
        """Validate the input for this module.
        This will call the relevant submethod, located as validate_{type}.
        You always get a tuple back, with the first value being True or False depending
        on if the input value was validated properly.
        The second value is the properly parsed value.
        So for example, calling validate('50') on a number setting would return (True, 50)
        """

        validator = getattr(self, f"validate_{self.type}", None)
        if validator is None:
            log.info(f"No validator available for type {type}")
            return True, value

        if not callable(validator):
            log.error(f"Validator is not callable {type}")
            return True, value

        return validator(value)

    def validate_text(self, value: str) -> Tuple[bool, str]:
        """Validate a text value"""
        value = value.strip()
        if "min_str_len" in self.constraints and len(value) < self.constraints["min_str_len"]:
            return (False, f"needs to be at least {self.constraints['min_str_len']} characters long")
        if "max_str_len" in self.constraints and len(value) > self.constraints["max_str_len"]:
            return (False, f"needs to be at most {self.constraints['max_str_len']} characters long")
        return True, value

    def validate_number(self, str_value: str) -> Tuple[bool, Union[str, int]]:
        """Validate a number value"""
        try:
            value = int(str_value)
        except ValueError:
            return False, "Not a valid integer"

        if "min_value" in self.constraints and value < self.constraints["min_value"]:
            return (False, f"needs to have a value that is at least {self.constraints['min_value']}")
        if "max_value" in self.constraints and value > self.constraints["max_value"]:
            return (False, f"needs to have a value that is at most {self.constraints['max_value']}")
        return True, value

    @staticmethod
    def validate_boolean(value: str) -> Tuple[bool, bool]:
        """Validate a boolean value"""
        return True, value == "on"

    def validate_options(self, value: str) -> Tuple[bool, str]:
        """Validate a options value"""
        return value in self.options, value


class ModuleType:
    TYPE_NORMAL = 1
    TYPE_ALWAYS_ENABLED = 2


class BaseModule:
    """
    This class will include all the basics that a module needs
    to be operable.
    """

    ID: str = __name__.split(".")[-1]
    NAME = "Base Module"
    DESCRIPTION = (
        "This is the description for the base module. "
        + "It's what will be shown on the website where you can enable "
        + "and disable modules."
    )
    # PAGE_DESCRIPTION is an optional longer description that is shown on the configure page
    PAGE_DESCRIPTION: Optional[str] = None
    SETTINGS: List[Any] = []
    ENABLED_DEFAULT = False
    PARENT_MODULE: Optional[Any] = None
    CATEGORY = "Uncategorized"
    HIDDEN = False
    MODULE_TYPE = ModuleType.TYPE_NORMAL
    CONFIGURE_LEVEL = 500

    def __init__(self, bot: Optional[Bot], config: Optional[Config] = None) -> None:
        """Initialize any dictionaries the module might or might not use.
        This is called once on bot startup, and once in the website whenever the module list is accessed"""
        self.bot = bot

        self.commands: Any = {}
        self.default_settings = {}
        self.settings: Any = {}
        self.submodules: Any = []
        self.parent_module: Optional[BaseModule] = None

        # We store a dictionary with the default settings for convenience
        for setting in self.SETTINGS:
            self.default_settings[setting.key] = setting.default

        self.db_module: Optional[Module] = None

    def load(self, **options: Any) -> BaseModule:
        """This method will load everything from the module into
        their proper dictionaries, which we can then use later."""

        self.settings = self.module_settings()

        self.commands = {}
        self.load_commands(**options)

        return self

    @classmethod
    def db_settings(cls) -> Dict[str, Any]:
        settings = {}
        with DBManager.create_session_scope() as session:
            module = session.query(Module).filter(Module.id == cls.ID).one()
            if module.settings is not None:
                try:
                    settings = json.loads(module.settings)
                except ValueError:
                    pass

        return settings

    @classmethod
    def module_settings(cls) -> Dict[str, Any]:
        settings = cls.db_settings()

        # Load any unset settings
        for setting in cls.SETTINGS:
            if setting.key not in settings:
                settings[setting.key] = setting.default

        return settings

    @classmethod
    def is_enabled(cls) -> bool:
        with DBManager.create_session_scope() as db_session:
            db_module = db_session.query(Module).filter_by(id=cls.ID).one_or_none()
            if db_module is None:
                return cls.ENABLED_DEFAULT
            else:
                return db_module.enabled

    def load_commands(self, **options: Any) -> None:
        pass

    def parse_settings(self, **in_settings: Dict[str, Any]) -> Union[Literal[False], Dict[str, Any]]:
        ret = {}
        for key, value in in_settings.items():
            setting = find(lambda setting: setting.key == key, self.SETTINGS)
            if setting is None:
                # We were passed a setting that's not available for this module
                return False
            log.debug(f"{key}: {value}")
            res, new_value = setting.validate(value)
            if res is False:
                # Something went wrong when validating one of the settings
                log.warning(new_value)
                return False

            ret[key] = new_value

        for setting in self.SETTINGS:
            if setting.type == "boolean":
                if setting.key not in ret:
                    ret[setting.key] = False
                    log.debug("{}: {} - special".format(setting.key, False))

        return ret

    def enable(self, bot: Optional[Bot]) -> None:
        pass

    def disable(self, bot: Optional[Bot]) -> None:
        pass

    def on_loaded(self) -> None:
        pass

    def get_phrase(self, key: str, **arguments: Any) -> str:
        if key not in self.settings:
            log.error("{} is not in this modules settings.")
            return "KeyError in get_phrase"

        try:
            return self.settings[key].format(**arguments)
        except (IndexError, ValueError, KeyError):
            log.warning(
                f'An error occured when formatting phrase "{self.settings[key]}". Arguments: ({arguments}) Will fall back to default phrase.'
            )

        try:
            return self.default_settings[key].format(**arguments)
        except:
            log.exception(f"ABORT - The default phrase {self.default_settings[key]} is BAD. Arguments: ({arguments})")

        return "FatalError in get_phrase"
