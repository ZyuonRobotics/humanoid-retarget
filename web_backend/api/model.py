"""Model API endpoints."""
import base64
import io
import json
import os
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException, UploadFile, File

from humanoid_retargeting import DATA_PATH, RETARGETING_PATH
from humanoid_retargeting.mjcf_generator import generator_class
from web_backend.api.schemas import MotionInfo

router = APIRouter(prefix="/api/model", tags=["model"])


@router.get("/motions/{generator_type}", response_model=list[MotionInfo])
async def list_motions(generator_type: str):
    """List available motion files."""
    motions = []

    data_path = Path(DATA_PATH)
    if not data_path.exists():
        return []

    for motion_file in data_path.glob(f"*.{generator_type}"):
        info = MotionInfo(
            filename=motion_file.name,
            type=generator_type
        )
        motions.append(info)

    return motions


@router.get("/motions/{generator_type}/{filename}")
async def get_motion_info(generator_type: str, filename: str):
    """Get detailed info about a motion file."""
    motion_path = Path(DATA_PATH) / f"{filename}"

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
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to load motion file")


@router.post("/retarget")
async def retarget_motion(
    motion_file: str,
    robot_name: str,
    generator_type: str,
    config_name: str,
    output_name: Optional[str] = None
):
    """Retarget a motion file to a robot."""
    from humanoid_retargeting.retargeter import Retargeter

    motion_path = Path(DATA_PATH) / motion_file
    if not motion_path.exists():
        raise HTTPException(status_code=404, detail="Motion file not found")

    if output_name is None:
        output_name = motion_path.stem + "_" + robot_name

    output_path = Path(RETARGETING_PATH) / f"{output_name}.npz"

    try:
        retargeter = Retargeter(
            source_file_path=str(motion_path),
            robot_name=robot_name,
            generator_type=generator_type,
            config_name=config_name,
            view=False
        )

        retargeter.run_ik(progress_bar=False)
        retargeter.save_as_npz(str(output_path), target_framerate=100)

        return {
            "status": "success",
            "output": str(output_path),
            "frame_count": retargeter.frame_num
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retarget/{output_name}")
async def get_retargeted_motion(output_name: str):
    """Get retargeted motion data."""
    output_path = Path(RETARGETING_PATH) / f"{output_name}.npz"

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


@router.post("/upload/motion")
async def upload_motion(file: UploadFile = File(...), generator_type: str = "bvh"):
    """Upload a motion file."""
    from web_backend.core.config import MAX_UPLOAD_SIZE

    # Ensure DATA_PATH directory exists
    data_path = Path(DATA_PATH)
    data_path.mkdir(parents=True, exist_ok=True)

    # Check file size
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    # Validate file type
    ext = Path(file.filename).suffix.lower()
    valid_exts = {".bvh", ".npz"}
    if ext not in valid_exts:
        raise HTTPException(status_code=400, detail="Invalid file type")

    # Save file
    save_path = data_path / file.filename
    try:
        save_path.write_bytes(content)
    except OSError as e:
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    return {
        "status": "uploaded",
        "filename": file.filename,
        "path": str(save_path)
    }


@router.post("/align-preview")
async def get_align_preview(
    source_file: str,
    robot_name: str,
    generator_type: str,
    retarget_config: dict
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

        # Reload mujoco with provided config
        aligner.load_mujoco(retarget_config=config)

        # Get calibrated qpos (this computes the aligned pose)
        qpos = aligner.cali_qpos.tolist()

        return {
            "xml": aligner.generator.xml_str,
            "qpos": qpos,
            "body_names": aligner.generator.all_body_names,
            "global_body_ratio": aligner.global_body_ratio
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/frame/{output_name}/{frame_id}")
async def get_frame_data(output_name: str, frame_id: int):
    """Get frame data for visualization."""
    output_path = Path(RETARGETING_PATH) / f"{output_name}.npz"

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
