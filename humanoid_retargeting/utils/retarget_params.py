from dataclasses import dataclass, field, fields, asdict, MISSING
from typing import Dict, List, Optional, Union
import json


@dataclass
class FootParams:
    left_name: Optional[str] = None
    right_name:  Optional[str] = None
    offset: float = 0.0

    def is_valid(self) -> bool:
        return self.left_name is not None and self.right_name is not None

@dataclass
class NeckParams:
    name: Optional[str] = None
    offset: float = 0.0

@dataclass
class TrackerConfig:
    human: List[str]
    robot: List[str]
    position_cost: float
    orientation_cost: float

    def __post_init__(self):
        assert len(self.human) == len(self.robot), "human and robot lists must have the same length"

@dataclass
class RetargetParams:
    robot_foot: FootParams = field(default_factory=FootParams)
    human_foot: FootParams = field(default_factory=FootParams)
    robot_neck: NeckParams = field(default_factory=NeckParams)
    human_neck: NeckParams = field(default_factory=NeckParams)
    base_x_shift: float = 0.0
    base_y_shift: float = 0.0
    extra_body_ratio:  Union[float, List[float]] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    relative_body_ratio_dict: Dict[str, Union[float, List[float]]] = field(default_factory=dict)
    body_rotate_dict: Dict[str, list] = field(default_factory=dict)
    tracker_dict: Dict[str, TrackerConfig] = field(default_factory=dict)

    def to_json(self, file_path: str) -> None:
        with open(file_path, 'w') as f:
            json.dump(asdict(self), f, indent=4)

    @classmethod
    def from_json(cls, file_path: str) -> 'RetargetParams':
        with open(file_path, 'r') as f:
            data = json.load(f)

        if 'robot_foot' in data:
            data['robot_foot'] = FootParams(**data['robot_foot'])
        if 'human_foot' in data:
            data['human_foot'] = FootParams(**data['human_foot'])
        if 'human_neck' in data:
            data['human_neck'] = NeckParams(**data['human_neck'])
        if 'robot_neck' in data:
            data['robot_neck'] = NeckParams(**data['robot_neck'])
        if 'tracker_dict' in data:
            for key, tracker_data in data['tracker_dict'].items():
                data['tracker_dict'][key] = TrackerConfig(**tracker_data)

        return cls(**data)
