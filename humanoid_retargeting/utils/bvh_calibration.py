# File: utils/bvh_offset_rotate.py

import os
from pathlib import Path
import json
import numpy as np
from scipy.spatial.transform import Rotation as R
from mujoco import MjModel, MjData

from humanoid_retargeting.motion_player.bvh_player import BVHPlayer
from humanoid_retargeting import BVH_DATA_PATH
from hurodes import ROBOTS_PATH

def rotate_offset_line(line: str) -> str:
    if not line.strip().startswith("OFFSET"):
        return line
    parts = line.strip().split()
    if len(parts) != 4:
        return line
    x, y, z = map(float, parts[1:])
    vec = np.array([x, y, z])

    # 先绕 X 轴 -90 度（Y-up 转为 Z-up），再绕 Z 轴 180 度（调整面向方向）
    r = R.from_euler('z', 90, degrees=True) * R.from_euler('x', 90, degrees=True)
    rotated = r.apply(vec)
    return f"OFFSET {rotated[0]:.6f} {rotated[1]:.6f} {rotated[2]:.6f}\n"

def rotate_bvh_offset_to_z_up(input_bvh_path: str, output_bvh_path: str):
    """
    将 BVH 文件中骨架的 OFFSET 坐标从 Y-up 坐标系转换为 Z-up(MuJoCo)坐标系，
    即绕 X 轴 -90° 旋转，保留动作数据不变。

    Args:
        input_bvh_path: 原始 BVH 文件路径(Y-up 坐标系）
        output_bvh_path: 修改后的 BVH 文件输出路径(Z-up 坐标系）
    """
    with open(input_bvh_path, 'r') as f:
        lines = f.readlines()

    motion_start = next(i for i, l in enumerate(lines) if l.strip().startswith("Frame Time"))
    header = lines[:motion_start + 1]
    motion = lines[motion_start + 1:]

    rotated_header = [rotate_offset_line(line) for line in header]

    with open(output_bvh_path, 'w') as f:
        f.writelines(rotated_header + motion)

    print(f"✅ Converted OFFSETs to Z-up and saved to {output_bvh_path}")
    return output_bvh_path


def create_calibrated_bvh_path(input_bvh_path: str) -> str:
    """
    给定 BVH 文件路径，返回添加 "_calibrated" 后缀的新路径。
    例如："pose.bvh" → "pose_calibrated.bvh"
    """
    base, ext = os.path.splitext(input_bvh_path)
    return f"{base}_calibrated{ext}"


def generate_retarget_params_from_model(model: MjModel, data: MjData, output_path: str = "retarget_params.json") -> str:
    """
    根据已有的 mujoco 模型和数据提取关键信息，生成初始版本的 retarget_params.json 文件。

    参数：
        model: mujoco.MjModel - 已加载的人体模型
        data: mujoco.MjData - 与模型对应的数据
        output_path: str - 要保存的 JSON 路径

    返回：
        输出文件路径
    """
    all_body_names = [model.body(i).name for i in range(model.nbody) if "world" not in model.body(i).name]
    z_positions = {name: data.body(name).xpos[2] for name in all_body_names}

    sorted_by_z = sorted(z_positions.items(), key=lambda x: x[1])
    left_foot, right_foot = sorted_by_z[0][0], sorted_by_z[1][0]

    neck_candidates = [name for name in all_body_names if "Head" in name or "Neck" in name]
    neck_name = neck_candidates[0] if neck_candidates else ""

    base_candidates = [name for name in all_body_names if "Pelvis" in name or "Spine" in name or "Hip" in name]
    base_name = base_candidates[0] if base_candidates else all_body_names[0]
    base_x_shift = float(data.body(base_name).xpos[0])
    base_y_shift = float(data.body(base_name).xpos[1])

    # 默认机器人脚与脖子（需后期手动替换）
    robot_foot = {
        "left_name": "leg_l6_link",
        "right_name": "leg_r6_link",
        "offset": -0.06
    }
    robot_neck = {
        "name": "zhead_1_link",
        "offset": 0.0
    }

    params = {
        "robot_foot": robot_foot,
        "human_foot": {
            "left_name": left_foot,
            "right_name": right_foot,
            "offset": -0.01
        },
        "robot_neck": robot_neck,
        "human_neck": {
            "name": neck_name,
            "offset": 0.0
        },
        "base_x_shift": round(base_x_shift, 4),
        "base_y_shift": round(base_y_shift, 4),
        "extra_body_ratio": [1.0, 1.0, 1.0],
        "relative_body_ratio_dict": {},
        "body_rotate_dict": {},
        "tracker_dict": {}
    }

    with open(output_path, 'w') as f:
        json.dump(params, f, indent=2)

    print(f"✅ Generated retarget_params: {output_path}")
    return output_path


if __name__ == '__main__':
    INPUT_PATH = os.path.join(BVH_DATA_PATH, "Reallusion", "myData", 'BJJ_General_02.bvh')
    OUTPUT_PATH = create_calibrated_bvh_path(INPUT_PATH)
    rotate_bvh_offset_to_z_up(INPUT_PATH, OUTPUT_PATH)
    
    res = os.path.join(ROBOTS_PATH, "kuavo_s45", "retargeting", "bvh")
    Retarget_Params_Path = os.path.join(res, "try.json")
    player = BVHPlayer(INPUT_PATH)
    player.render_first_frame()
    generate_retarget_params_from_model(player.model, player.data, Retarget_Params_Path)
    