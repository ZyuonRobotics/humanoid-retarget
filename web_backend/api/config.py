"""Configuration API endpoints."""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File

from humanoid_retargeting import CONFIGS_PATH
from humanoid_retargeting.utils.retarget_config import RetargetConfig, TrackerConfig
from web_backend.api.schemas import RobotInfo, BodyTreeNode, TrackerConfigSchema, RetargetConfigSchema

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/robots", response_model=List[RobotInfo])
async def get_robots():
    """Get list of available robots."""
    robots = []
    configs_path = Path(CONFIGS_PATH)

    if configs_path.exists():
        for robot_dir in configs_path.iterdir():
            if robot_dir.is_dir():
                for gen_type_dir in robot_dir.iterdir():
                    if gen_type_dir.is_dir():
                        robots.append(RobotInfo(
                            name=robot_dir.name,
                            generator_type=gen_type_dir.name
                        ))

    # Add default robots if no configs exist
    if not robots:
        robots = [
            RobotInfo(name="zhaplin-21dof", generator_type="bvh"),
            RobotInfo(name="zhaplin-21dof", generator_type="smpl"),
        ]

    return robots


def build_tree(joint_names, joint_parents, parent_idx=-1):
    """Recursively build tree structure from joint names and parent indices."""
    import numpy as np

    tree = []
    for idx, parent_idx_in_parents in enumerate(joint_parents):
        if parent_idx_in_parents == parent_idx:
            children = build_tree(joint_names, joint_parents, idx)
            tree.append({
                "title": joint_names[idx],
                "key": joint_names[idx],
                "children": children if children else None
            })
    return tree


# Default SMPL/SMPLH joint hierarchy (kintree_table)
# This is the standard SMPL joint parent structure
SMPL_JOINT_PARENTS = [
    -1,  # 0: pelvis (root)
    0,   # 1: left_hip
    0,   # 2: right_hip
    0,   # 3: spine1
    1,   # 4: left_knee
    2,   # 5: right_knee
    3,   # 6: spine2
    4,   # 7: left_ankle
    5,   # 8: right_ankle
    6,   # 9: spine3
    7,   # 10: left_foot
    8,   # 11: right_foot
    9,   # 12: neck
    9,   # 13: left_collar
    9,   # 14: right_collar
    12,  # 15: head
    13,  # 16: left_shoulder
    14,  # 17: right_shoulder
    16,  # 18: left_elbow
    17,  # 19: right_elbow
    18,  # 20: left_wrist
    19,  # 21: right_wrist
]


@router.get("/{robot_name}/{generator_type}/body-tree", response_model=Dict)
async def get_body_tree(robot_name: str, generator_type: str):
    """Get body tree structure for human and robot."""
    import xml.etree.ElementTree as ET
    import numpy as np

    from hurodes.generators import MJCFHumanoidGenerator
    from humanoid_retargeting.mjcf_generator import generator_class

    result = {
        "human": {},
        "robot": {}
    }

    # Get robot body tree from MJCF XML
    try:
        robot_generator = MJCFHumanoidGenerator.from_robot_name(robot_name)
        robot_generator.generate(relative_mesh_path=False)

        # Parse MJCF XML to get body hierarchy
        xml_str = robot_generator.xml_str
        root = ET.fromstring(xml_str)

        # Find worldbody and get all body elements
        worldbody = root.find(".//worldbody")
        if worldbody is not None:
            bodies = {}

            def parse_body(elem, parent_name=None):
                """Recursively parse body elements."""
                name = elem.get("name")
                if name:
                    bodies[name] = parent_name
                    for child in elem.findall("body"):
                        parse_body(child, name)

            for body in worldbody.findall("body"):
                parse_body(body, None)

            # Build tree structure
            if bodies:
                # Find root (body with no parent)
                root_bodies = [name for name, parent in bodies.items() if parent is None]
                if root_bodies:
                    # Build tree from root
                    robot_tree = []
                    for root_name in root_bodies:
                        def build_body_tree(body_name):
                            children = [build_body_tree(child_name) for child_name, parent in bodies.items() if parent == body_name]
                            return {
                                "title": body_name,
                                "key": body_name,
                                "children": children if children else None
                            }
                        robot_tree.append(build_body_tree(root_name))

                    result["robot"] = robot_tree
                else:
                    result["robot"] = []
            else:
                result["robot"] = []

    except Exception as e:
        result["robot"] = {"error": str(e)}

    # Get human body tree from generator_class
    try:
        if generator_type not in generator_class:
            result["human"] = {"error": f"Unknown generator type: {generator_type}"}
        else:
            gen_class = generator_class[generator_type]

            # Create generator instance (without loading a file)
            generator = gen_class()

            # For BVH, we need to provide default joint_names and joint_parents
            # For SMPL, we need to load a file to get the structure

            if generator_type == "smpl":
                # Use default SMPL joint names and parents
                from humanoid_retargeting.mjcf_generator.constants import SMPL_JOINT_NAMES
                result["human"] = build_tree(SMPL_JOINT_NAMES, SMPL_JOINT_PARENTS)
            elif generator_type == "bvh":
                # For BVH, we need a motion file to get the structure
                result["human"] = {
                    "note": "Human body structure for BVH requires a motion file to be loaded"
                }
            elif hasattr(generator, 'joint_names') and generator.joint_names:
                # If generator already has joint_names (like SMPL with default joints)
                joint_names = generator.joint_names
                joint_parents = generator.joint_parents
                if joint_names is not None and joint_parents is not None:
                    result["human"] = build_tree(joint_names, joint_parents.tolist() if isinstance(joint_parents, np.ndarray) else joint_parents)
                else:
                    result["human"] = {
                        "note": "Human body structure requires a motion file to be loaded"
                    }
            else:
                result["human"] = {
                    "note": "Human body structure requires a motion file to be loaded"
                }
    except Exception as e:
        result["human"] = {"error": str(e)}

    return result


@router.get("/{robot_name}/{generator_type}/configs", response_model=List[str])
async def list_configs(robot_name: str, generator_type: str):
    """List available config names for a robot."""
    config_dir = Path(CONFIGS_PATH) / robot_name / generator_type

    if not config_dir.exists():
        return []

    configs = []
    for f in config_dir.glob("*.yaml"):
        configs.append(f.stem)

    return configs


@router.get("/{robot_name}/{generator_type}/{config_name}", response_model=RetargetConfigSchema)
async def get_config(robot_name: str, generator_type: str, config_name: str):
    """Get a specific config."""
    config_path = Path(CONFIGS_PATH) / robot_name / generator_type / f"{config_name}.yaml"

    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Config not found")

    config = RetargetConfig.from_yaml(str(config_path))

    # Convert to schema
    tracker_dict = {}
    for key, tracker in config.tracker_dict.items():
        tracker_dict[key] = TrackerConfigSchema(
            human=tracker.human,
            robot=tracker.robot,
            position_cost=tracker.position_cost,
            orientation_cost=tracker.orientation_cost
        )

    return RetargetConfigSchema(
        base_x_shift=config.base_x_shift,
        base_y_shift=config.base_y_shift,
        base_rotation=config.base_rotation,
        body_rotate_dict=config.body_rotate_dict,
        extra_body_ratio=config.extra_body_ratio if isinstance(config.extra_body_ratio, list) else [config.extra_body_ratio],
        relative_body_ratio_dict=config.relative_body_ratio_dict,
        damping_cost=config.damping_cost,
        tracker_dict=tracker_dict
    )


@router.post("/{robot_name}/{generator_type}/{config_name}")
async def save_config(
    robot_name: str,
    generator_type: str,
    config_name: str,
    config: RetargetConfigSchema
):
    """Save a config."""
    config_dir = Path(CONFIGS_PATH) / robot_name / generator_type
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / f"{config_name}.yaml"

    # Convert schema to config
    tracker_dict = {}
    for key, tracker in config.tracker_dict.items():
        tracker_dict[key] = TrackerConfig(
            human=tracker.human,
            robot=tracker.robot,
            position_cost=tracker.position_cost,
            orientation_cost=tracker.orientation_cost
        )

    retarget_config = RetargetConfig(
        base_x_shift=config.base_x_shift,
        base_y_shift=config.base_y_shift,
        base_rotation=config.base_rotation,
        body_rotate_dict=config.body_rotate_dict,
        extra_body_ratio=config.extra_body_ratio,
        relative_body_ratio_dict=config.relative_body_ratio_dict,
        damping_cost=config.damping_cost,
        tracker_dict=tracker_dict
    )

    retarget_config.to_yaml(str(config_path))

    return {"status": "saved", "path": str(config_path)}


@router.delete("/{robot_name}/{generator_type}/{config_name}")
async def delete_config(robot_name: str, generator_type: str, config_name: str):
    """Delete a config."""
    config_path = Path(CONFIGS_PATH) / robot_name / generator_type / f"{config_name}.yaml"

    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Config not found")

    try:
        config_path.unlink()
    except OSError as e:
        raise HTTPException(status_code=500, detail="Failed to delete config file")

    return {"status": "deleted"}


@router.post("/upload")
async def upload_config(file: UploadFile = File(...)):
    """Upload a config YAML file."""
    content = await file.read()

    # Validate it's valid YAML
    import yaml
    try:
        yaml.safe_load(content)
    except yaml.YAMLError:
        raise HTTPException(status_code=400, detail="Invalid YAML file")

    # Save to temp location
    from web_backend.core.config import UPLOAD_DIR
    save_path = UPLOAD_DIR / file.filename
    try:
        save_path.write_bytes(content)
    except OSError:
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    return {"status": "uploaded", "path": str(save_path)}
