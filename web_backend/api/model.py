"""Model API endpoints."""
import logging
import base64
import io
import json
import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException, UploadFile, File

from humanoid_retargeting import DATA_PATH, RETARGETING_PATH, GENERATOR_TYPE_TO_DATA_PATH, PLAYER_FILE_SUFFIXES
from humanoid_retargeting.mjcf_generator import generator_class
from humanoid_retargeting.utils.human_config import HumanConfigNotFoundError
from web_backend.api.schemas import MotionInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/model", tags=["model"])


@router.get("/motions/tree")
async def list_motions_tree():
    """Return nested motion file tree structure."""
    tree = {}

    for gen_type, data_path in GENERATOR_TYPE_TO_DATA_PATH.items():
        tree[gen_type] = _scan_directory(Path(data_path), DATA_PATH)

    return tree


def _scan_directory(path: Path, root_path: Path) -> dict:
    """Recursively scan directory for motion files."""
    result = {"motions": [], "subdirs": {}}
    if not path.exists():
        return result

    for item in sorted(path.iterdir()):
        if item.is_file():
            ext = item.suffix.lower()
            if ext in ('.bvh', '.npz'):
                result["motions"].append({
                    "filename": item.name,
                    "relative_path": str(item.relative_to(root_path)),
                    "type": ext.lstrip('.')
                })
        elif item.is_dir():
            result["subdirs"][item.name] = _scan_directory(item, root_path)
    return result


@router.get("/motions/{generator_type}", response_model=list[MotionInfo])
async def list_motions(generator_type: str):
    """List available motion files."""
    motions = []

    data_path = Path(GENERATOR_TYPE_TO_DATA_PATH.get(generator_type, DATA_PATH))
    if not data_path.exists():
        return []

    ext = PLAYER_FILE_SUFFIXES.get(generator_type, generator_type)

    for motion_file in data_path.rglob(f"*.{ext}"):
        info = MotionInfo(
            filename=str(motion_file.relative_to(data_path)),
            type=generator_type
        )
        motions.append(info)

    return motions


@router.get("/motions/{generator_type}/{filename}")
async def get_motion_info(generator_type: str, filename: str):
    """Get detailed info about a motion file."""
    motion_path = Path(GENERATOR_TYPE_TO_DATA_PATH.get(generator_type, DATA_PATH)) / f"{filename}"

    if not motion_path.exists():
        raise HTTPException(status_code=404, detail="Motion file not found")

    # Try to load and get info
    try:
        if generator_type == "bvh":
            from humanoid_retargeting.motion_player import BVHPlayer
            player = BVHPlayer.from_source_file_path(str(motion_path))
        elif generator_type == "smpl":
            from humanoid_retargeting.motion_player import SMPLPlayer
            player = SMPLPlayer.from_source_file_path(str(motion_path))
        else:
            raise HTTPException(status_code=400, detail="Invalid generator type")

        return {
            "filename": filename,
            "type": generator_type,
            "frame_count": player.frame_num,
            "frame_rate": player.frame_rate,
            "body_names": player.all_body_names
        }
    except Exception as e:
        logger.error(f"Failed to load motion file '{filename}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load motion file")


@router.post("/retarget-preview")
async def retarget_preview(
    motion_file: str,
    robot_name: str,
    generator_type: str,
    config_name: str,
    output_name: Optional[str] = None
):
    """Run retarget and return preview data without saving. Stores data in session for later save."""
    from humanoid_retargeting.retargeter import Retargeter

    motion_path = Path(DATA_PATH) / motion_file
    if not motion_path.exists():
        raise HTTPException(status_code=404, detail="Motion file not found")

    if output_name is None:
        output_name = motion_path.stem + "_" + robot_name

    # Store output_name in module-level dict for later save
    global _pending_retarget
    _pending_retarget = {
        "output_name": output_name,
        "robot_name": robot_name
    }

    try:
        retargeter = Retargeter(
            source_file_path=str(motion_path),
            robot_name=robot_name,
            generator_type=generator_type,
            config_name=config_name,
            view=False
        )

        retargeter.run_ik(progress_bar=False)

        # Store retargeter in module-level dict for later save
        _pending_retarget["retargeter"] = retargeter

        # Get body transforms for combined human-robot visualization
        body_transforms = retargeter.get_all_frame_body_transforms()

        # Get model info for combined visualization
        body_names = retargeter.generator.all_body_names

        return {
            "status": "success",
            "output_name": output_name,
            "robot_name": robot_name,
            "frame_num": retargeter.frame_num,
            "frame_rate": retargeter.frame_rate,
            "body_names": list(body_names),
            "nbody": retargeter.model.nbody,
            "xml": retargeter.generator.xml_str,
            "body_transforms": body_transforms
        }
    except HumanConfigNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Module-level storage for pending retarget data
_pending_retarget: dict = {}


@router.post("/save-retarget")
async def save_retarget():
    """Save the pending retarget result that was generated by retarget-preview."""
    global _pending_retarget

    if "retargeter" not in _pending_retarget:
        raise HTTPException(status_code=400, detail="No pending retarget to save. Please run retarget-preview first.")

    retargeter = _pending_retarget["retargeter"]
    output_name = _pending_retarget["output_name"]
    robot_name = _pending_retarget["robot_name"]

    output_path = Path(RETARGETING_PATH) / robot_name / f"{output_name}.npz"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        retargeter.save_as_npz(str(output_path), target_framerate=100)

        # Clear pending data
        _pending_retarget = {}

        return {
            "status": "success",
            "output": str(output_path),
            "frame_count": retargeter.frame_num
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retarget/{robot_name}/{output_name}")
async def get_retargeted_motion(robot_name: str, output_name: str):
    """Get retargeted motion data."""
    output_path = Path(RETARGETING_PATH) / robot_name / f"{output_name}.npz"

    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Retargeted motion not found")

    data = np.load(str(output_path), allow_pickle=True)

    return {
        "filename": output_name,
        "qpos": data["qpos"].tolist(),
        "qvel": data.get("qvel", np.zeros((len(data["qpos"]), 1))).tolist(),
        "frame_count": len(data["qpos"]),
        "framerate": float(data.get("framerate", 100))
    }


@router.get("/retargeted/{robot_name}")
async def list_retargeted_motions(robot_name: str):
    """List all retargeted motion files for a specific robot."""
    robot_dir = Path(RETARGETING_PATH) / robot_name
    if not robot_dir.exists():
        return []

    motions = []
    for f in robot_dir.glob("*.npz"):
        motions.append(f.stem)

    return sorted(motions)


@router.get("/mjcf/{robot_name}")
async def get_robot_mjcf(robot_name: str):
    """Get MJCF XML for a robot."""
    from hurodes.generators import MJCFHumanoidGenerator
    from hurodes import HumanoidRobot

    try:
        generator = MJCFHumanoidGenerator.from_robot_name(robot_name)
        generator.generate(relative_mesh_path=False)

        # Get robot info
        robot = HumanoidRobot.from_name(robot_name)

        return {
            "robot_name": robot_name,
            "xml": generator.xml_str,
            "body_names": generator.all_body_names,
            "joint_names": robot.hrdf.joint_name_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mjcf/{robot_name}/with-meshes")
async def get_robot_mjcf_with_meshes(robot_name: str):
    """Get MJCF XML for a robot with mesh files encoded as base64."""
    return _get_robot_mjcf_with_meshes_cached(robot_name)


@lru_cache(maxsize=32)
def _get_robot_mjcf_with_meshes_cached(robot_name: str):
    """Cached implementation — robot mesh data is static per robot."""

    from hurodes.generators import MJCFHumanoidGenerator
    from hurodes import HumanoidRobot

    try:
        generator = MJCFHumanoidGenerator.from_robot_name(robot_name)
        generator.generate(relative_mesh_path=False)

        # Get robot info
        robot = HumanoidRobot.from_name(robot_name)

        # Read mesh directory
        mesh_dir = robot.hrdf.hrdf_path / "meshes"
        meshes = {}
        if mesh_dir.exists():
            for mesh_file in mesh_dir.glob("*.stl"):
                with open(mesh_file, "rb") as f:
                    meshes[mesh_file.name] = base64.b64encode(f.read()).decode("utf-8")

        return {
            "robot_name": robot_name,
            "xml": generator.xml_str,
            "body_names": generator.all_body_names,
            "joint_names": robot.hrdf.joint_name_list,
            "meshes": meshes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/motion")
async def upload_motion(file: UploadFile = File(...), generator_type: str = "bvh"):
    """Upload a motion file."""
    from web_backend.core.config import MAX_UPLOAD_SIZE

    # Validate filename - prevent path traversal attacks
    filename = file.filename or ""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename: path traversal not allowed")

    # Ensure DATA_PATH directory exists
    data_path = Path(DATA_PATH)
    data_path.mkdir(parents=True, exist_ok=True)

    # Check file size
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    # Validate file type
    ext = Path(filename).suffix.lower()
    valid_exts = {".bvh": "bvh", ".npz": "smpl"}
    if ext not in list(valid_exts.keys()):
        raise HTTPException(status_code=400, detail="Invalid file type")

    # Save file
    save_path = data_path / valid_exts[ext] / filename
    try:
        save_path.write_bytes(content)
    except OSError as e:
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    return {
        "status": "uploaded",
        "filename": filename,
        "path": str(save_path)
    }


@router.post("/upload/robot-motion/{robot_name}")
async def upload_robot_motion(robot_name: str, file: UploadFile = File(...)):
    """Upload a robot retargeted motion file."""
    from web_backend.core.config import MAX_UPLOAD_SIZE

    # Validate filename - prevent path traversal attacks
    filename = file.filename or ""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename: path traversal not allowed")

    # Ensure robot directory exists
    robot_dir = Path(RETARGETING_PATH) / robot_name
    robot_dir.mkdir(parents=True, exist_ok=True)

    # Check file size
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    # Validate file type (must be .npz for robot motions)
    ext = Path(filename).suffix.lower()
    if ext != ".npz":
        raise HTTPException(status_code=400, detail="Invalid file type: only .npz is allowed for robot motions")

    # Save file
    save_path = robot_dir / filename
    try:
        save_path.write_bytes(content)
    except OSError as e:
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    return {
        "status": "uploaded",
        "filename": filename,
        "path": str(save_path)
    }


@router.post("/upload/human-motion")
async def upload_human_motion(file: UploadFile = File(...)):
    """Upload a human motion file. Path is determined by file extension."""
    from web_backend.core.config import MAX_UPLOAD_SIZE

    # Validate filename - prevent path traversal attacks
    filename = file.filename or ""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename: path traversal not allowed")

    # Check file size
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    # Validate and determine file type by extension
    ext = Path(filename).suffix.lower()
    ext_to_gen_type = {".bvh": "bvh", ".npz": "smpl"}
    if ext not in ext_to_gen_type:
        raise HTTPException(status_code=400, detail="Invalid file type")

    generator_type = ext_to_gen_type[ext]
    data_path = Path(GENERATOR_TYPE_TO_DATA_PATH.get(generator_type, DATA_PATH))
    data_path.mkdir(parents=True, exist_ok=True)

    # Save file
    save_path = data_path / filename
    try:
        save_path.write_bytes(content)
    except OSError as e:
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    return {
        "status": "uploaded",
        "filename": filename,
        "path": str(save_path),
        "generator_type": generator_type
    }


@router.post("/align-preview")
async def get_align_preview(
    source_file: str,
    robot_name: str,
    generator_type: str,
    retarget_config: dict,
    generate_skin: bool = True
):
    """Get align preview with combined human-robot MJCF and calibrated initial pose."""
    from humanoid_retargeting.aligner import Aligner
    from humanoid_retargeting.utils.retarget_config import RetargetConfig, TrackerConfig

    motion_path = Path(DATA_PATH) / source_file
    if not motion_path.exists():
        raise HTTPException(status_code=404, detail="Motion file not found")

    # Convert retarget_config dict to RetargetConfig object
    tracker_dict = {}
    for key, tracker_data in retarget_config.get('tracker_dict', {}).items():
        tracker_dict[key] = TrackerConfig(
            human=tracker_data['human'],
            robot=tracker_data['robot'],
            position_cost=tracker_data['position_cost'],
            orientation_cost=tracker_data['orientation_cost']
        )

    config = RetargetConfig(
        base_x_shift=retarget_config.get('base_x_shift', 0.0),
        base_y_shift=retarget_config.get('base_y_shift', 0.0),
        base_rotation=retarget_config.get('base_rotation', [0.0, 0.0, 0.0]),
        body_rotate_dict=retarget_config.get('body_rotate_dict', {}),
        extra_body_ratio=retarget_config.get('extra_body_ratio', [1.0, 1.0, 1.0]),
        relative_body_ratio_dict=retarget_config.get('relative_body_ratio_dict', {}),
        damping_cost=retarget_config.get('damping_cost', 5.0),
        tracker_dict=tracker_dict
    )

    try:
        aligner = Aligner(
            source_file_path=str(motion_path),
            robot_name=robot_name,
            generator_type=generator_type,
            config_name=None,
            view=False
        )

        # Store generate_skin parameter for later use
        aligner.generate_skin = generate_skin

        # Reload mujoco with provided config and generate_skin parameter
        aligner.load_mujoco(retarget_config=config, generate_skin=generate_skin)

        # Get calibrated qpos (this computes the aligned pose)
        qpos = aligner.cali_qpos.tolist()

        return {
            "xml": aligner.generator.xml_str,
            "qpos": qpos,
            "body_names": aligner.generator.all_body_names,
            "global_body_ratio": aligner.global_body_ratio
        }
    except HumanConfigNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/human-preview")
async def get_human_preview(
    source_file: str,
    generator_type: str,
    retarget_config: dict,
    generate_skin: bool = True
):
    """Get human-only MJCF and calibrated initial pose (no robot)."""
    import mujoco
    from humanoid_retargeting.aligner import Aligner
    from humanoid_retargeting.utils.retarget_config import RetargetConfig, TrackerConfig

    motion_path = Path(DATA_PATH) / source_file
    if not motion_path.exists():
        raise HTTPException(status_code=404, detail="Motion file not found")

    # Convert retarget_config dict to RetargetConfig (same shape as align-preview)
    tracker_dict = {}
    for key, tracker_data in retarget_config.get('tracker_dict', {}).items():
        tracker_dict[key] = TrackerConfig(
            human=tracker_data['human'],
            robot=tracker_data['robot'],
            position_cost=tracker_data['position_cost'],
            orientation_cost=tracker_data['orientation_cost']
        )
    config = RetargetConfig(
        base_x_shift=retarget_config.get('base_x_shift', 0.0),
        base_y_shift=retarget_config.get('base_y_shift', 0.0),
        base_rotation=retarget_config.get('base_rotation', [0.0, 0.0, 0.0]),
        body_rotate_dict=retarget_config.get('body_rotate_dict', {}),
        extra_body_ratio=retarget_config.get('extra_body_ratio', [1.0, 1.0, 1.0]),
        relative_body_ratio_dict=retarget_config.get('relative_body_ratio_dict', {}),
        damping_cost=retarget_config.get('damping_cost', 5.0),
        tracker_dict=tracker_dict,
    )

    try:
        # Aligner needs a robot_name to construct a composite; we reuse it and
        # then slice out the human half. Any valid robot produces the same
        # human qpos since the human half is independent of the robot.
        from hurodes import HumanoidRobot
        robots = HumanoidRobot.list_robots()
        if not robots:
            raise HTTPException(status_code=500, detail="No robots available to derive human preview")
        robot_name = robots[0]

        aligner = Aligner(
            source_file_path=str(motion_path),
            robot_name=robot_name,
            generator_type=generator_type,
            config_name=None,
            view=False
        )

        # Store generate_skin parameter for later use
        aligner.generate_skin = generate_skin

        aligner.load_mujoco(retarget_config=config, generate_skin=generate_skin)

        # Human-only model from the composite's human generator
        human_xml = aligner.human_generator.xml_str
        human_model = mujoco.MjModel.from_xml_string(human_xml)  # type: ignore

        # In the composite model, human bodies come first, so the human qpos
        # is the leading slice of cali_qpos.
        full_qpos = aligner.cali_qpos
        human_qpos = full_qpos[: human_model.nq].tolist()

        return {
            "xml": human_xml,
            "qpos": human_qpos,
            "body_names": aligner.human_generator.all_body_names,
            "global_body_ratio": aligner.global_body_ratio,
        }
    except HTTPException:
        raise
    except HumanConfigNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/frame/{robot_name}/{output_name}/{frame_id}")
async def get_frame_data(robot_name: str, output_name: str, frame_id: int):
    """Get frame data for visualization."""
    output_path = Path(RETARGETING_PATH) / robot_name / f"{output_name}.npz"

    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Retargeted motion not found")

    data = np.load(str(output_path), allow_pickle=True)

    if frame_id < 0 or frame_id >= len(data["qpos"]):
        raise HTTPException(status_code=400, detail="Invalid frame_id")

    return {
        "frame_id": frame_id,
        "qpos": data["qpos"][frame_id].tolist(),
        "qvel": data["qvel"][frame_id].tolist() if "qvel" in data else None
    }


@router.get("/player/robot/{robot_name}/motion/{motion_file}")
async def get_robot_player_motion_data(robot_name: str, motion_file: str):
    """Pre-compute all frame body transforms for player motion.

    Returns body positions and quaternions for every frame so the frontend
    can render by just updating mesh transforms without re-computing physics.
    """
    from humanoid_retargeting.motion_player import RobotMotionPlayer
    from hurodes import HumanoidRobot

    motion_path = Path(RETARGETING_PATH) / robot_name / f"{motion_file}.npz"
    if not motion_path.exists():
        raise HTTPException(status_code=404, detail="Motion file not found")

    try:
        robot = HumanoidRobot.from_name(robot_name)
        player = RobotMotionPlayer(robot_name=robot_name, view=False)
        player.load(source_file_path=str(motion_path), hrdf=robot.hrdf)

        body_transforms = player.get_all_frame_body_transforms()

        return {
            "robot_name": robot_name,
            "motion_file": motion_file,
            "frame_num": int(player.frame_num),
            "frame_rate": float(player.frame_rate),
            "body_names": list(player.generator.all_body_names),
            "nbody": int(player.model.nbody),
            "body_transforms": body_transforms,
            "frameRate": float(player.frame_rate),
        }
    except Exception as e:
        logger.error(f"Failed to get player motion data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/player/human/{generator_type}/motion/{motion_file:path}")
async def get_human_player_motion_data(generator_type: str, motion_file: str, generate_skin: bool = True):
    """Pre-compute all frame body transforms for human motion player.

    Returns body positions and quaternions for every frame so the frontend
    can render by just updating mesh transforms without re-computing physics.
    Supports SMPL and BVH formats.
    """
    from humanoid_retargeting.motion_player import PLAYERS_CLASS

    # Get motion file path based on generator type
    # motion_file may include generator_type prefix (e.g., "smpl/elegant.npz"), strip it if present
    if motion_file.startswith(f"{generator_type}/"):
        motion_file = motion_file[len(f"{generator_type}/"):]
    motion_path = Path(GENERATOR_TYPE_TO_DATA_PATH.get(generator_type, DATA_PATH)) / motion_file
    if not motion_path.exists():
        raise HTTPException(status_code=404, detail="Motion file not found")

    try:
        # Get appropriate player class
        player_class = PLAYERS_CLASS.get(generator_type)
        if not player_class:
            raise HTTPException(status_code=400, detail=f"Unsupported generator type: {generator_type}")

        # Create player with generate_skin parameter for SMPL
        if generator_type == "smpl":
            player = player_class(view=False, global_body_ratio=1.0, relative_body_ratio_dict=None)
            # Set generate_skin on generator before loading
            player.generator.generate_skin = generate_skin
        else:
            player = player_class(view=False, global_body_ratio=1.0, relative_body_ratio_dict=None)

        # Load motion file
        player.load(source_file_path=str(motion_path))
        player.apply_adjustments()

        # Pre-compute all frame body transforms
        body_transforms = player.get_all_frame_body_transforms()

        # Get MJCF XML with skin data (already generated by accessing player.model in get_all_frame_body_transforms)
        xml_str = player.generator.xml_str

        # Log XML info for debugging
        logger.info(f"Generated XML length: {len(xml_str)}, has_skin: {generator_type == 'smpl' and generate_skin}")
        if len(xml_str) < 1000:
            logger.warning(f"XML seems too short: {xml_str[:500]}")

        return {
            "generator_type": generator_type,
            "motion_file": motion_file,
            "frame_num": int(player.frame_num),
            "frame_rate": float(player.frame_rate),
            "body_names": list(player.generator.all_body_names),
            "nbody": int(player.model.nbody),
            "body_transforms": body_transforms,
            "frameRate": float(player.frame_rate),
            "xml": xml_str,
            "has_skin": generator_type == "smpl" and generate_skin,
        }
    except Exception as e:
        logger.error(f"Failed to get human player motion data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/player/human/{generator_type}/config/{motion_file:path}")
async def get_human_player_config(generator_type: str, motion_file: str):
    """Get HumanConfig for a motion file. Creates default config if none exists."""
    from humanoid_retargeting.motion_player import PLAYERS_CLASS

    # motion_file may include generator_type prefix (e.g., "smpl/elegant.npz"), strip it if present
    if motion_file.startswith(f"{generator_type}/"):
        motion_file = motion_file[len(f"{generator_type}/"):]
    motion_path = Path(GENERATOR_TYPE_TO_DATA_PATH.get(generator_type, DATA_PATH)) / motion_file
    if not motion_path.exists():
        raise HTTPException(status_code=404, detail="Motion file not found")

    try:
        player_class = PLAYERS_CLASS.get(generator_type)
        if not player_class:
            raise HTTPException(status_code=400, detail=f"Unsupported generator type: {generator_type}")

        player = player_class(view=False, global_body_ratio=1.0, relative_body_ratio_dict=None)
        player.load(source_file_path=str(motion_path))

        # Return HumanConfig as dict
        return {
            "height_adjustment": player.human_config.height_adjustment,
            "hip_names": player.human_config.hip_names,
            "hip_offset": player.human_config.hip_offset,
            "foot_names": player.human_config.foot_names,
            "foot_offset": player.human_config.foot_offset,
            "joint_adjustments": player.human_config.joint_adjustments,
        }
    except Exception as e:
        logger.error(f"Failed to get human player config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/player/human/{generator_type}/config/{motion_file:path}")
async def save_human_player_config(generator_type: str, motion_file: str, config: dict):
    """Save HumanConfig for a motion file."""
    from humanoid_retargeting.motion_player import PLAYERS_CLASS

    # motion_file may include generator_type prefix (e.g., "smpl/elegant.npz"), strip it if present
    if motion_file.startswith(f"{generator_type}/"):
        motion_file = motion_file[len(f"{generator_type}/"):]
    motion_path = Path(GENERATOR_TYPE_TO_DATA_PATH.get(generator_type, DATA_PATH)) / motion_file
    if not motion_path.exists():
        raise HTTPException(status_code=404, detail="Motion file not found")

    try:
        player_class = PLAYERS_CLASS.get(generator_type)
        if not player_class:
            raise HTTPException(status_code=400, detail=f"Unsupported generator type: {generator_type}")

        player = player_class(view=False, global_body_ratio=1.0, relative_body_ratio_dict=None)
        player.load(source_file_path=str(motion_path))

        # Update human_config with provided values
        # If height_adjustment is None, auto-calculate it
        if "height_adjustment" in config:
            if config["height_adjustment"] is None:
                # Auto-calculate height_adjustment
                player.calculate_height_adjustment(draw_plot=False)
            else:
                player.human_config.height_adjustment = config["height_adjustment"]
        if "hip_names" in config:
            player.human_config.hip_names = config["hip_names"]
        if "hip_offset" in config:
            player.human_config.hip_offset = config["hip_offset"]
        if "foot_names" in config:
            player.human_config.foot_names = config["foot_names"]
        if "foot_offset" in config:
            player.human_config.foot_offset = config["foot_offset"]
        if "joint_adjustments" in config:
            player.human_config.joint_adjustments = config["joint_adjustments"]

        # Save config to yaml file
        player.save_config(str(motion_path))

        return {"status": "saved", "config": {
            "height_adjustment": player.human_config.height_adjustment,
            "hip_names": player.human_config.hip_names,
            "hip_offset": player.human_config.hip_offset,
            "foot_names": player.human_config.foot_names,
            "foot_offset": player.human_config.foot_offset,
            "joint_adjustments": player.human_config.joint_adjustments,
        }}
    except Exception as e:
        logger.error(f"Failed to save human player config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/split-motion")
async def split_motion(generator_type: str, motion_file: str, split_indices: str):
    """Split a motion file into multiple parts at the specified indices.

    Args:
        generator_type: 'bvh' or 'smpl'
        motion_file: relative path to the motion file (may include generator_type prefix)
        split_indices: comma-separated frame indices to split at (e.g., "300,400" creates segments 0-300, 300-400, 400-end)
    """
    # Strip generator_type prefix if present (motion_file may include prefix like "smpl/file.npz")
    if motion_file.startswith(f"{generator_type}/"):
        motion_file = motion_file[len(f"{generator_type}/"):]
    motion_path = Path(GENERATOR_TYPE_TO_DATA_PATH.get(generator_type, DATA_PATH)) / motion_file
    if not motion_path.exists():
        raise HTTPException(status_code=404, detail="Motion file not found")

    # Parse split indices
    try:
        indices = [int(idx.strip()) for idx in split_indices.split(',') if idx.strip()]
        if not indices:
            raise ValueError("No valid indices provided")
        # Sort and validate indices
        indices = sorted(set(indices))
        if any(idx < 0 for idx in indices):
            raise HTTPException(status_code=400, detail="All split indices must be non-negative")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid split_indices format: {e}")

    try:
        if generator_type == "smpl":
            data_dict = np.load(motion_path)
            data_length = data_dict["poses"].shape[0]

            # Validate all indices
            if any(idx >= data_length for idx in indices):
                raise HTTPException(status_code=400, detail=f"All split indices must be less than data length ({data_length})")

            # Create segments: [0, idx1), [idx1, idx2), ..., [idxN, end)
            segment_ranges = []
            start = 0
            for idx in indices:
                segment_ranges.append((start, idx))
                start = idx
            segment_ranges.append((start, data_length))

            # Save all segments
            output_files = []
            for start_idx, end_idx in segment_ranges:
                if start_idx >= end_idx:
                    continue

                segment_part = {
                    "gender": data_dict['gender'],
                    "mocap_framerate": data_dict["mocap_framerate"],
                    "poses": data_dict["poses"][start_idx:end_idx],
                    "trans": data_dict["trans"][start_idx:end_idx],
                    "betas": data_dict["betas"]
                }

                segment_path = motion_path.parent / f"{motion_path.stem}_{start_idx}_{end_idx}.npz"
                np.savez_compressed(segment_path, **segment_part)
                output_files.append({
                    "file": str(segment_path),
                    "range": f"{start_idx}-{end_idx}"
                })

            return {
                "status": "success",
                "segments": output_files
            }

        elif generator_type == "bvh":
            # Read BVH file and split
            with open(motion_path, 'r') as f:
                content = f.read()

            # Find the MOTION section
            motion_idx = content.upper().find('MOTION')
            if motion_idx == -1:
                raise HTTPException(status_code=400, detail="Invalid BVH file: no MOTION section found")

            header = content[:motion_idx]
            motion_section = content[motion_idx:]

            # Parse frames
            lines = motion_section.strip().split('\n')
            frames_line_idx = None
            for i, line in enumerate(lines):
                if line.strip().upper().startswith('FRAMES:'):
                    frames_line_idx = i
                    break

            if frames_line_idx is None:
                raise HTTPException(status_code=400, detail="Invalid BVH file: no FRAMES line found")

            frames = int(lines[frames_line_idx].split(':')[1].strip())

            # Find where the motion data starts (after the frame time line)
            motion_data_start = motion_idx
            for i in range(frames_line_idx + 2, len(lines)):
                if lines[i].strip():
                    motion_data_start = content.find(lines[i].strip(), motion_idx)
                    break

            header_content = content[:motion_data_start]
            motion_data = content[motion_data_start:]

            # Split motion data into lines (each line is a frame)
            motion_lines = [line.strip() for line in motion_data.strip().split('\n') if line.strip()]

            # Validate all indices
            if any(idx >= len(motion_lines) for idx in indices):
                raise HTTPException(status_code=400, detail=f"All split indices must be less than frame count ({len(motion_lines)})")

            # Create segments: [0, idx1), [idx1, idx2), ..., [idxN, end)
            segment_ranges = []
            start = 0
            for idx in indices:
                segment_ranges.append((start, idx))
                start = idx
            segment_ranges.append((start, len(motion_lines)))

            # Save all segments
            output_files = []
            for start_idx, end_idx in segment_ranges:
                if start_idx >= end_idx:
                    continue

                segment_motion_data = '\n'.join(motion_lines[start_idx:end_idx])
                segment_bvh = header_content + segment_motion_data + '\n'

                # Update frames count
                segment_bvh = segment_bvh.replace(f"Frames: {frames}", f"Frames: {end_idx - start_idx}")

                segment_path = motion_path.parent / f"{motion_path.stem}_{start_idx}_{end_idx}.bvh"
                with open(segment_path, 'w') as f:
                    f.write(segment_bvh)

                output_files.append({
                    "file": str(segment_path),
                    "range": f"{start_idx}-{end_idx}"
                })

            return {
                "status": "success",
                "segments": output_files
            }

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported generator type: {generator_type}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to split motion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
