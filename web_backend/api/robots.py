"""Robot information API endpoints."""
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from hurodes import HumanoidRobot
from web_backend.api.schemas import (
    ActuatorInfoSchema,
    BodyTreeNodeSchema,
    JointInfoSchema,
    RobotDetailSchema,
)

router = APIRouter(prefix="/api/robots", tags=["robots"])


def build_body_tree(body_list: List, body_parent_id: List[int]) -> List[Dict[str, Any]]:
    """Build tree structure from body list and parent IDs."""
    if not body_list or not body_parent_id:
        return []

    # Create a mapping from id to body name and mass
    id_to_body = {}
    for body in body_list:
        flat = body.to_flat_dict()
        body_id = flat.get("id")
        if body_id is not None:
            id_to_body[body_id] = {
                "name": flat.get("name", ""),
                "mass": flat.get("mass"),
            }

    # Build children mapping
    children_map: Dict[int, List[int]] = {}
    for idx, parent_id in enumerate(body_parent_id):
        if parent_id not in children_map:
            children_map[parent_id] = []
        children_map[parent_id].append(idx)

    # Recursive build tree
    def build_node(body_id: int) -> Dict[str, Any]:
        body_info = id_to_body.get(body_id, {"name": f"body_{body_id}", "mass": None})
        node = {
            "name": body_info["name"],
            "id": body_id,
            "mass": body_info.get("mass"),
            "children": [],
        }
        for child_id in children_map.get(body_id, []):
            node["children"].append(build_node(child_id))
        return node

    # Find root (body with parent -1)
    root_ids = [idx for idx, pid in enumerate(body_parent_id) if pid == -1]
    return [build_node(rid) for rid in root_ids]


@router.get("", response_model=List[str])
async def get_robot_list():
    """Get list of available robot names from hurodes."""
    return HumanoidRobot.list_robots()


@router.get("/{robot_name}", response_model=RobotDetailSchema)
async def get_robot_detail(robot_name: str):
    """Get detailed information about a specific robot."""
    try:
        robot = HumanoidRobot.from_name(robot_name)
        hrdf = robot.hrdf
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Robot not found: {robot_name}")

    # Build joint info
    joints = []
    for joint_name in hrdf.joint_name_list:
        joint_range = hrdf.joint_range_dict.get(joint_name)
        if joint_range is not None:
            joints.append(JointInfoSchema(
                name=joint_name,
                range=joint_range.tolist() if hasattr(joint_range, 'tolist') else list(joint_range)
            ))

    # Build actuator info
    actuators = []
    for joint_name in hrdf.joint_name_list:
        peak_vel = hrdf.actuator_peak_velocity_dict.get(joint_name, 0.0)
        peak_torque = hrdf.actuator_peak_torque_dict.get(joint_name, 0.0)
        actuators.append(ActuatorInfoSchema(
            joint_name=joint_name,
            peak_velocity=float(peak_vel),
            peak_torque=float(peak_torque)
        ))

    # Build body tree
    body_tree = build_body_tree(hrdf.info_list_dict.get("body", []), hrdf.body_parent_id)

    # Build IMU dict
    imu_dict = {}
    for imu_config in hrdf.imu_config_list:
        imu_dict[imu_config.body_name] = imu_config.model_dump()

    # Build motor dict
    motor_dict = {}
    for motor_config in hrdf.motor_config_list:
        motor_dict[motor_config.name] = motor_config.model_dump()

    return RobotDetailSchema(
        name=robot_name,
        joints=joints,
        actuators=actuators,
        body_tree=[BodyTreeNodeSchema(**node) for node in body_tree],
        base_height=hrdf.base_height,
        hip_names=hrdf.hip_names,
        knee_names=hrdf.knee_names,
        foot_names=hrdf.foot_names,
        torso_name=hrdf.torso_name,
        imu_dict=imu_dict,
        motor_dict=motor_dict,
    )


@router.get("/{robot_name}/joints", response_model=List[JointInfoSchema])
async def get_robot_joints(robot_name: str):
    """Get joint information for a specific robot."""
    try:
        robot = HumanoidRobot.from_name(robot_name)
        hrdf = robot.hrdf
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Robot not found: {robot_name}")

    joints = []
    for joint_name in hrdf.joint_name_list:
        joint_range = hrdf.joint_range_dict.get(joint_name)
        if joint_range is not None:
            joints.append(JointInfoSchema(
                name=joint_name,
                range=joint_range.tolist() if hasattr(joint_range, 'tolist') else list(joint_range)
            ))

    return joints


@router.get("/{robot_name}/actuators", response_model=List[ActuatorInfoSchema])
async def get_robot_actuators(robot_name: str):
    """Get actuator information for a specific robot."""
    try:
        robot = HumanoidRobot.from_name(robot_name)
        hrdf = robot.hrdf
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Robot not found: {robot_name}")

    actuators = []
    for joint_name in hrdf.joint_name_list:
        peak_vel = hrdf.actuator_peak_velocity_dict.get(joint_name, 0.0)
        peak_torque = hrdf.actuator_peak_torque_dict.get(joint_name, 0.0)
        actuators.append(ActuatorInfoSchema(
            joint_name=joint_name,
            peak_velocity=float(peak_vel),
            peak_torque=float(peak_torque)
        ))

    return actuators


@router.get("/{robot_name}/body-tree")
async def get_robot_body_tree(robot_name: str):
    """Get body tree structure for a specific robot."""
    try:
        robot = HumanoidRobot.from_name(robot_name)
        hrdf = robot.hrdf
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Robot not found: {robot_name}")

    body_tree = build_body_tree(hrdf.info_list_dict.get("body", []), hrdf.body_parent_id)
    return body_tree