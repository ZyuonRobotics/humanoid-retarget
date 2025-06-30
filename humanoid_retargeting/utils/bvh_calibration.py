# File: utils/bvh_calibration.py

import os
import json
from mujoco import MjModel, MjData

from humanoid_retargeting.motion_player.bvh_player import BVHPlayer
from humanoid_retargeting import BVH_DATA_PATH
from hurodes import ROBOTS_PATH

def generate_retarget_params_from_model(model: MjModel, data: MjData, output_path: str = "retarget_params.json") -> str:
    """
    Extract key information from an existing mujoco model and data to generate 
    an initial version of retarget_params.json file.

    Args:
        model: mujoco.MjModel - Loaded humanoid model
        data: mujoco.MjData - Corresponding data for the model
        output_path: str - Path to save the JSON file

    Returns:
        Output file path
    """
    # Get all body names excluding 'world'
    all_body_names = [model.body(i).name for i in range(model.nbody) if "world" not in model.body(i).name]
    
    # Get Z positions of all bodies
    z_positions = {name: data.body(name).xpos[2] for name in all_body_names}

    # Sort bodies by Z position to find feet (lowest positions)
    sorted_by_z = sorted(z_positions.items(), key=lambda x: x[1])
    left_foot, right_foot = sorted_by_z[0][0], sorted_by_z[1][0]

    # Find neck/head body
    neck_candidates = [name for name in all_body_names if "Head" in name or "Neck" in name]
    neck_name = neck_candidates[0] if neck_candidates else ""

    # Find base body (pelvis/spine/hip)
    base_candidates = [name for name in all_body_names if "Pelvis" in name or "Spine" in name or "Hip" in name]
    base_name = base_candidates[0] if base_candidates else all_body_names[0]
    base_x_shift = float(data.body(base_name).xpos[0])
    base_y_shift = float(data.body(base_name).xpos[1])

    # Default robot foot parameters
    robot_foot = {
        "left_name": "leg_l6_link",
        "right_name": "leg_r6_link",
        "offset": -0.06
    }
    
    # Default robot neck parameters
    robot_neck = {
        "name": "zhead_1_link",
        "offset": 0.0
    }

    # Initialize body scaling and rotation parameters
    relative_body_ratio_dict = {}
    body_rotate_dict = {}

    for name in all_body_names:
        lname = name.lower()
        
        # Shoulder rotation correction
        if "upperarm" in lname:
            if "l" in lname:  # Left arm
                body_rotate_dict[name] = [0, 0, -90]  # Rotate -90 degrees around Z-axis
                relative_body_ratio_dict[name] = 2.2  # Scale factor
            elif "r" in lname:  # Right arm
                body_rotate_dict[name] = [0, 0, 90]   # Rotate 90 degrees around Z-axis
                relative_body_ratio_dict[name] = 2.2   # Scale factor

        # Forearm scaling
        if "forearm" in lname:
            relative_body_ratio_dict[name] = 1.8
            
        # Head scaling
        if "head" in lname:
            relative_body_ratio_dict[name] = 1.2  # Scale neck length
            
        # Clavicle scaling
        if "clavicle" in lname:
            relative_body_ratio_dict[name] = 0.82

    # Compile all parameters
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
        "extra_body_ratio": [1.0, 1.0, 1.0],  # Global scaling factors
        "relative_body_ratio_dict": relative_body_ratio_dict,  # Per-body scaling
        "body_rotate_dict": body_rotate_dict,    # Per-body rotation
        "base_rotation": [90, 0, 90],           # Initial model rotation
        "tracker_dict": {}                      # Empty tracker mapping
    }

    # Save parameters to JSON file
    with open(output_path, 'w') as f:
        json.dump(params, f, indent=2)

    print(f"✅ Generated retarget_params: {output_path}")
    return output_path


if __name__ == '__main__':
    # Example usage
    INPUT_PATH = os.path.join(BVH_DATA_PATH, "Reallusion", "Folk Artistry - Ba Jia Jiang", 'test.bvh')
    res = os.path.join(ROBOTS_PATH, "kuavo_s45", "retargeting", "bvh")
    Retarget_Params_Path = os.path.join(res, "try.json")
    
    # Process BVH file
    player = BVHPlayer(INPUT_PATH)
    player.render_first_frame()
    generate_retarget_params_from_model(player.model, player.data, Retarget_Params_Path)