from pajbot.modules.base import BaseModule
from pajbot.modules.base import ModuleSetting


class WarningModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Warnings"
    DESCRIPTION = "Gives people warnings before timing them out for the full duration for banphrase and stuff"
    CATEGORY = "Filter"
    ENABLED_DEFAULT = True
    SETTINGS = [
        ModuleSetting(
            key="total_chances",
            label="How many warnings a user can receive before full timeout length",
            type="number",
            required=True,
            placeholder="",
            default=2,
            constraints={"min_value": 1, "max_value": 10},
        ),
        ModuleSetting(
            key="length",
            label="How long warnings last before they expire",
            type="number",
            required=True,
            placeholder="Warning expiration length in seconds",
            default=600,
            constraints={"min_value": 60, "max_value": 3600},
        ),
        ModuleSetting(
            key="base_timeout",
            label="Base timeout for warnings",
            type="number",
            required=True,
            placeholder="Base timeout length for warnings in seconds",
            default=10,
            constraints={"min_value": 5, "max_value": 30},
        ),
        ModuleSetting(
            key="redis_prefix",
            label="Prefix in the redis database. Only touch if you know what you're doing.",
            type="text",
            required=True,
            placeholder="Can be left blank, don't worry!",
            default="",
        ),
    ]
