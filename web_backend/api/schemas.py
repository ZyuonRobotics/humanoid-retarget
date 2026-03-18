"""Pydantic schemas for API request/response models."""
from typing import Any, Dict, List, Optional
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


class JointInfoSchema(BaseModel):
    """Joint information schema."""
    name: str
    range: List[float]


class ActuatorInfoSchema(BaseModel):
    """Actuator information schema."""
    joint_name: str
    peak_velocity: float
    peak_torque: float


class BodyTreeNodeSchema(BaseModel):
    """Body tree node schema for robot structure."""
    name: str
    id: int
    mass: Optional[float] = None
    children: List["BodyTreeNodeSchema"] = []


class RobotDetailSchema(BaseModel):
    """Robot detailed information schema."""
    name: str
    joints: List[JointInfoSchema]
    actuators: List[ActuatorInfoSchema]
    body_tree: List[BodyTreeNodeSchema]
    base_height: float
    hip_names: List[str]
    knee_names: List[str]
    foot_names: List[str]
    torso_name: str
    imu_dict: Dict[str, Any]
    motor_dict: Dict[str, Any]


# Update forward references
BodyTreeNode.model_rebuild()
BodyTreeNodeSchema.model_rebuild()
