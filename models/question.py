from dataclasses import dataclass, field

@dataclass(frozen=True)
class Question:
    id: str
    page_id: str
    label: str
    type: str
    required: bool = True
    max_selections: int = 1
    options: tuple[str, ...] = ()
    validation: dict = field(default_factory=dict)