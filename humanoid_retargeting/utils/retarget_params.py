import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Union

@dataclass
class TrackerConfig:
    human: List[str]
    robot: List[str]
    position_cost: Union[float, List[float]]
    orientation_cost: Union[float, List[float]]

    def __post_init__(self):
        assert len(self.human) == len(self.robot), "human and robot lists must have the same length"


@dataclass
class RetargetParams:
    base_x_shift: float = 0.0
    base_y_shift: float = 0.0

    base_rotation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    body_rotate_dict: Dict[str, list] = field(default_factory=dict)

    extra_body_ratio: Union[float, List[float]] = field(default_factory=lambda: [1.0, 1.0, 1.0]) 
    relative_body_ratio_dict: Dict[str, Union[float, List[float]]] = field(default_factory=dict)

    damping_cost: float = 5.0
    tracker_dict: Dict[str, TrackerConfig] = field(default_factory=dict)

    def to_json(self, file_path: str) -> None:
        with open(file_path, 'w') as f:
            json.dump(asdict(self), f, indent=4)

    @classmethod
    def from_json(cls, file_path: str) -> 'RetargetParams':
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict) -> 'RetargetParams':
        if 'tracker_dict' in data:
            for key, tracker_data in data['tracker_dict'].items():
                data['tracker_dict'][key] = TrackerConfig(**tracker_data)

        return cls(**data)
