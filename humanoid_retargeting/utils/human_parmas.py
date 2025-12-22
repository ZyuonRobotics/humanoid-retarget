import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


@dataclass
class HumanParams:
    height_adjustment: Optional[float] = None
    hip_names: Optional[list[str]] = None
    hip_offset: Optional[float] = None
    foot_names: Optional[list[str]] = None
    foot_offset: Optional[float] = None
    joint_adjustments: Dict[str, List[float]] = field(default_factory=dict)

    def to_json(self, file_path: str) -> None:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=4, ensure_ascii=False)

    @classmethod
    def from_json(cls, file_path: str) -> 'HumanParams':
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict) -> 'HumanParams':
        return cls(**data)

    def is_valid(self) -> bool:
        return not any(value is None for value in asdict(self).values())
