from typing import Dict, List, Optional

from hurodes.utils.config import BaseConfig

class HumanConfig(BaseConfig):
    height_adjustment: Optional[float] = None
    hip_names: Optional[List[str]] = None
    hip_offset: Optional[float] = None
    foot_names: Optional[List[str]] = None
    foot_offset: Optional[float] = None
    joint_adjustments: Dict[str, List[float]] = {}

    def is_valid(self) -> bool:
        return not self.has_none

class HumanConfigNotFoundError(Exception):
    """Raised when a motion file doesn't have a corresponding human config."""
    pass
