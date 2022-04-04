from dataclasses import dataclass, field

import marshmallow_dataclass


@dataclass
class Pagination:
    offset: int = field(default=0)
    limit: int = field(default=30)
    direction: str = field(default="asc")


PaginationSchema = marshmallow_dataclass.class_schema(Pagination)
