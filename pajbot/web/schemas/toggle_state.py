from dataclasses import dataclass

import marshmallow_dataclass


@dataclass
class ToggleState:
    new_state: bool


ToggleStateSchema = marshmallow_dataclass.class_schema(ToggleState)
