from pathlib import Path
from typing import Dict, List, Optional, Union

from hurodes.utils.config import BaseConfig
from pydantic import model_validator

from humanoid_retargeting import CONFIGS_PATH


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

    @classmethod
    def load(cls, robot_name: str, generator_type: str, config_name: str) -> Optional['RetargetConfig']:
        """Load a config from file. Returns None if not found.

        Args:
            robot_name: Robot name (e.g., "zhaplin-21dof")
            generator_type: Generator type ("smpl" or "bvh")
            config_name: Config name (without .yaml extension)

        Returns:
            RetargetConfig instance or None if file doesn't exist
        """
        config_path = cls._get_config_path(robot_name, generator_type, config_name)
        if not config_path.exists():
            return None
        return cls.from_yaml(str(config_path))

    def save(self, robot_name: str, generator_type: str, config_name: str) -> Path:
        """Save config to file.

        Args:
            robot_name: Robot name (e.g., "zhaplin-21dof")
            generator_type: Generator type ("smpl" or "bvh")
            config_name: Config name (without .yaml extension)

        Returns:
            Path to the saved config file
        """
        config_path = self._get_config_path(robot_name, generator_type, config_name)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        self.to_yaml(str(config_path))
        return config_path

    @classmethod
    def create_default(cls, robot_name: str, generator_type: str) -> 'RetargetConfig':
        """Create a default config in memory (without saving to file).

        Args:
            robot_name: Robot name (e.g., "zhaplin-21dof")
            generator_type: Generator type ("smpl" or "bvh")

        Returns:
            RetargetConfig instance with default values
        """
        return cls(
            base_x_shift=0.0,
            base_y_shift=0.0,
            base_rotation=[0.0, 0.0, 0.0],
            body_rotate_dict={},
            extra_body_ratio=[1.0, 1.0, 1.0],
            relative_body_ratio_dict={},
            damping_cost=5.0,
            tracker_dict={}
        )

    @staticmethod
    def _get_config_path(robot_name: str, generator_type: str, config_name: str) -> Path:
        """Get the path to a config file.

        Args:
            robot_name: Robot name
            generator_type: Generator type
            config_name: Config name

        Returns:
            Path to the config file
        """
        return CONFIGS_PATH / robot_name / generator_type / f"{config_name}.yaml"
