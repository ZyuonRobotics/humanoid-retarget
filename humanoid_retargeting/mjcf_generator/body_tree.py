"""Body tree utilities for human and robot skeletons."""
from typing import Dict, List, Any

from hurodes.generators import MJCFHumanoidGenerator


def build_body_tree(joint_names: List[str], joint_parents: List[int], parent_idx: int = -1) -> List[Dict[str, Any]]:
    """Recursively build tree structure from joint names and parent indices.

    Args:
        joint_names: List of joint names
        joint_parents: List of parent indices (same length as joint_names)
        parent_idx: Parent index to search for children (default -1 for root)

    Returns:
        List of tree nodes with 'name' and 'children' fields
    """
    tree = []
    for idx, parent_idx_in_parents in enumerate(joint_parents):
        if parent_idx_in_parents == parent_idx:
            children = build_body_tree(joint_names, joint_parents, idx)
            tree.append({
                "name": joint_names[idx],
                "children": children if children else None
            })
    return tree


def get_human_body_tree(generator_type: str, file_path: str = None) -> Dict[str, Any]:
    """Get human body tree for a generator type.

    Args:
        generator_type: Either "smpl" or "bvh"
        file_path: Optional path to motion file. If provided, uses Player to get
                   the actual skeleton structure. Required for BVH, can be used for SMPL too.

    Returns:
        Dict with human body tree or error message
    """
    if generator_type not in ["smpl", "bvh"]:
        return {"error": f"Unknown generator type: {generator_type}"}

    if file_path:
        # Use Player to get the actual skeleton structure from the motion file
        if generator_type == "smpl":
            from humanoid_retargeting.motion_player import SMPLPlayer
            player = SMPLPlayer.from_source_file_path(file_path)
        elif generator_type == "bvh":
            from humanoid_retargeting.motion_player import BVHPlayer
            player = BVHPlayer.from_source_file_path(file_path)

        return build_body_tree(player.generator.joint_names, player.generator.joint_parents.tolist())
    else:
        # Without a file, SMPL can use default constants, but BVH cannot
        if generator_type == "smpl":
            from humanoid_retargeting.mjcf_generator.constants import SMPL_JOINT_NAMES, SMPL_JOINT_PARENTS
            return build_body_tree(SMPL_JOINT_NAMES, SMPL_JOINT_PARENTS)
        else:
            return {
                "note": f"Human body structure for {generator_type} requires a motion file to be loaded"
            }


def get_robot_body_tree(robot_name: str) -> Dict[str, Any]:
    """Get robot body tree from MJCFHumanoidGenerator.

    Args:
        robot_name: Name of the robot

    Returns:
        Dict with robot body tree or error message
    """
    try:
        robot_generator = MJCFHumanoidGenerator.from_robot_name(robot_name)
        return robot_generator.get_body_tree_dict()
    except Exception as e:
        return {"error": str(e)}