import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Union


@dataclass
class FootParams:
    left_name: Optional[str] = None
    right_name: Optional[str] = None
    offset: float = 0.0

    def is_valid(self) -> bool:
        return self.left_name is not None and self.right_name is not None


@dataclass
class HipParams:
    left_name: Optional[str] = None
    right_name: Optional[str] = None
    offset: float = 0.0

    def is_valid(self) -> bool:
        return self.left_name is not None and self.right_name is not None


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
    robot_foot: FootParams = field(default_factory=FootParams)
    human_foot: FootParams = field(default_factory=FootParams)
    base_x_shift: float = 0.0
    base_y_shift: float = 0.0

    base_rotation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    body_rotate_dict: Dict[str, list] = field(default_factory=dict)

    robot_hip: HipParams = field(default_factory=HipParams)
    human_hip: HipParams = field(default_factory=HipParams)
    extra_body_ratio: Union[float, List[float]] = field(default_factory=lambda: [1.0, 1.0, 1.0]) 
    relative_body_ratio_dict: Dict[str, Union[float, List[float]]] = field(default_factory=dict)

    damping_cost: float = 5.0
    tracker_dict: Dict[str, TrackerConfig] = field(default_factory=dict)
    base_rotation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])  # new parameter to rotate the whole body

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
        clean: Dict = {}

        for key in ("robot_foot", "human_foot"):
            if key in data:
                f = data[key]
                clean[key] = FootParams(f["left_name"], f["right_name"], f["offset"])
        for key in ("robot_hip", "human_hip"):
            if key in data:
                h = data[key]
                clean[key] = HipParams(h["left_name"], h["right_name"], h["offset"])

        clean.update({
            "base_x_shift":   data.get("base_x_shift", 0.0),
            "base_y_shift":   data.get("base_y_shift", 0.0),
            "base_rotation":  data.get("base_rotation", [0.0, 0.0, 0.0]),
            "extra_body_ratio": data.get("extra_body_ratio", [1.0, 1.0, 1.0]),
            "relative_body_ratio_dict": {k: v for k, v in data.get("relative_body_ratio_dict", {}).items()},
            "body_rotate_dict":         {k: v for k, v in data.get("body_rotate_dict", {}).items()},
        })

        track_raw = data.get("tracker_dict", {})
        track_clean: Dict[str, TrackerConfig] = {}
        for part, cfg in track_raw.items():
            track_clean[part] = TrackerConfig(
                human=[x for x in cfg["human"]],
                robot=[x for x in cfg["robot"]],
                position_cost=cfg.get("position_cost", 100),
                orientation_cost=cfg.get("orientation_cost", 50),
            )
        clean["tracker_dict"] = track_clean

        defaults = cls()
        for k in asdict(defaults):
            clean.setdefault(k, getattr(defaults, k))

        return cls(**clean)