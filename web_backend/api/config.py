"""Configuration API endpoints."""
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Query

from humanoid_retargeting import CONFIGS_PATH, DATA_PATH, get_human_body_tree, get_robot_body_tree
from humanoid_retargeting.utils.retarget_config import RetargetConfig, TrackerConfig
from web_backend.api.schemas import RobotInfo, TrackerConfigSchema, RetargetConfigSchema

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


@router.get("/{robot_name}/{generator_type}/body-tree", response_model=Dict)
async def get_body_tree(
    robot_name: str,
    generator_type: str,
    motion_file: Optional[str] = Query(None, description="Motion file path for human body tree")
):
    """Get body tree structure for human and robot."""
    # Prepend data path to motion_file for human body tree
    if motion_file:
        motion_file = str(DATA_PATH/ motion_file)
    result = {
        "human": get_human_body_tree(generator_type, motion_file) if motion_file else {"note": "configPanel.selectMotionFileHint"},
        "robot": get_robot_body_tree(robot_name)
    }
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
    """Get a specific config. Returns in-memory default if not found (does not save to file)."""
    config = RetargetConfig.load(robot_name, generator_type, config_name)
    if config is None:
        config = RetargetConfig.create_default(robot_name, generator_type)

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
    """Save a config (only endpoint that writes to file)."""
    # Convert schema to config
    tracker_dict = {}
    for key, tracker in config.tracker_dict.items():
        tracker_dict[key] = TrackerConfig(
            human=tracker.human,
            robot=tracker.robot,
            position_cost=tracker.position_cost,
            orientation_cost=tracker.orientation_cost
        )
    base_rot = [90.0, 0.0, 90.0] if generator_type == "bvh" else [0.0, 0.0, 0.0]
    retarget_config = RetargetConfig(
        base_x_shift=config.base_x_shift,
        base_y_shift=config.base_y_shift,
        base_rotation=base_rot,
        body_rotate_dict=config.body_rotate_dict,
        extra_body_ratio=config.extra_body_ratio,
        relative_body_ratio_dict=config.relative_body_ratio_dict,
        damping_cost=config.damping_cost,
        tracker_dict=tracker_dict
    )

    saved_path = retarget_config.save(robot_name, generator_type, config_name)

    return {"status": "saved", "path": str(saved_path)}


@router.delete("/{robot_name}/{generator_type}/{config_name}")
async def delete_config(robot_name: str, generator_type: str, config_name: str):
    """Delete a config."""
    config_path = Path(CONFIGS_PATH) / robot_name / generator_type / f"{config_name}.yaml"

    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Config not found")

    try:
        config_path.unlink()
    except OSError:
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