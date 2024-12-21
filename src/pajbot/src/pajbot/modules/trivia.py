import logging

from pajbot.modules import BaseModule, ModuleSetting

log = logging.getLogger(__name__)


class TriviaModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Trivia"
    DESCRIPTION = "No longer functional :("
    CATEGORY = "Game"
    SETTINGS = [
        ModuleSetting(
            key="hint_count",
            label="How many hints the user should get before the question is ruined.",
            type="number",
            required=True,
            default=2,
            constraints={"min_value": 0, "max_value": 4},
        ),
        ModuleSetting(
            key="step_delay",
            label="Time between each step (step_delay*(hint_count+1) = length of each question)",
            type="number",
            required=True,
            placeholder="",
            default=10,
            constraints={"min_value": 5, "max_value": 45},
        ),
        ModuleSetting(
            key="default_point_bounty",
            label="Default point bounty per right answer",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="question_delay",
            label="Delay between questions in seconds.",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 600},
        ),
        ModuleSetting(
            key="commands_level",
            label="Minimum level to use !trivia start/stop",
            type="number",
            required=True,
            placeholder="",
            default=500,
            constraints={"min_value": 100, "max_value": 1500},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)
