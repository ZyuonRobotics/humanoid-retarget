from typing import Dict, List, Union

from hurodes.utils.config import BaseConfig
from pydantic import model_validator


class TrackerConfig(BaseConfig):
    human: List[str]
    robot: List[str]
    position_cost: Union[float, List[float]]
    orientation_cost: Union[float, List[float]]

    @model_validator(mode='after')
    def validate_lists_length(self):
        assert len(self.human) == len(self.robot), "human and robot lists must have the same length"
        return self


class RetargetConfig(BaseConfig):
    base_x_shift: float = 0.0
    base_y_shift: float = 0.0

    base_rotation: List[float] = [0.0, 0.0, 0.0]
    body_rotate_dict: Dict[str, list] = {}

    extra_body_ratio: Union[float, List[float]] = [1.0, 1.0, 1.0] 
    relative_body_ratio_dict: Dict[str, Union[float, List[float]]] = {}

    damping_cost: float = 5.0
    tracker_dict: Dict[str, TrackerConfig] = {}

    @classmethod
    def from_dict(cls, data: Dict) -> 'RetargetConfig':
        # Convert tracker_dict entries to TrackerConfig objects
        if 'tracker_dict' in data:
            for key, tracker_data in data['tracker_dict'].items():
                if not isinstance(tracker_data, TrackerConfig):
                    data['tracker_dict'][key] = TrackerConfig(**tracker_data)

        return cls(**data)
