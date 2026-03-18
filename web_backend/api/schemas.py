"""Pydantic schemas for API request/response models."""
from typing import Dict, List, Optional
from pydantic import BaseModel


class RobotInfo(BaseModel):
    """Robot information schema."""
    name: str
    generator_type: str


class BodyTreeNode(BaseModel):
    """Body tree node schema."""
    name: str
    children: List["BodyTreeNode"] = []


class TrackerConfigSchema(BaseModel):
    """Tracker configuration schema."""
    human: List[str]
    robot: List[str]
    position_cost: float
    orientation_cost: float


class RetargetConfigSchema(BaseModel):
    """Retarget configuration schema."""
    base_x_shift: float = 0.0
    base_y_shift: float = 0.0
    base_rotation: List[float] = [0.0, 0.0, 0.0]
    body_rotate_dict: Dict[str, List[float]] = {}
    extra_body_ratio: List[float] = [1.0, 1.0, 1.0]
    relative_body_ratio_dict: Dict[str, List[float]] = {}
    damping_cost: float = 5.0
    tracker_dict: Dict[str, TrackerConfigSchema] = {}


class MotionInfo(BaseModel):
    """Motion file information schema."""
    filename: str
    type: str
    frame_count: Optional[int] = None
    frame_rate: Optional[float] = None


# Update forward references
BodyTreeNode.model_rebuild()
