from humanoid_retargeting.constant.robot_data import kuavo_s40
from humanoid_retargeting.constant.robot_data import kuavo_s42
from humanoid_retargeting.constant.robot_data import kuavo_s45

ROBOT_DATA_DICT = {
    "kuavo_s40": {
        "height":1.26,
        "foot_thickness": 0.04,
        "body_tree": kuavo_s40.body_tree,
        "bodies_data": kuavo_s40.bodies_data
    },
    "kuavo_s42": {
        "height":1.4,
        "foot_thickness": 0.06,
        "body_tree": kuavo_s42.body_tree,
        "bodies_data": kuavo_s42.bodies_data
    },
    "kuavo_s45": {
        "height": 1.4,
        "foot_thickness": 0.06,
        "body_tree": kuavo_s45.body_tree,
        "bodies_data": kuavo_s45.bodies_data
    }
}


TRACKER_DICT = {
    "upper_base": {
        "smpl": ["left_collar", "right_collar"],
        "robot": ["base_link", "base_link"],
        "position_cost": 100.,
        "orientation_cost": 50.,
    },
    "lower_base": {
        "smpl": ["left_hip", "right_hip"],
        "robot": ["base_link", "base_link"],
        "position_cost": 100.,
        "orientation_cost": 50.,
    },
    "leg": {
        "smpl": ["left_knee", "left_ankle", "right_knee", "right_ankle"],
        "robot": ["leg_l4_link", "leg_l6_link", "leg_r4_link", "leg_r6_link"],
        "position_cost": 100.,
        "orientation_cost": 50.,
    },
    "foot": {
        "smpl": ["left_foot", "right_foot"],
        "robot": ["leg_l6_link", "leg_r6_link"],
        "position_cost": 200.,
        "orientation_cost": 50.,
    },
    "arm": {
        "smpl": ["left_elbow", "left_elbow", "right_elbow", "right_elbow"],
        "robot": ["zarm_l3_link", "zarm_l6_link", "zarm_r3_link", "zarm_r6_link"],
        "position_cost": 100.,
        "orientation_cost": 0.,
    },
    "hand": {
        "smpl": ["left_wrist", "right_wrist"],
        "robot": ["zarm_l5_link", "zarm_r5_link"],
        "position_cost": 100.,
        "orientation_cost": 0.,
    },
    "finger": {
        "smpl": ["left_index1", "left_pinky1", "right_index1", "right_pinky1"],
        "robot": ["zarm_l7_link", "zarm_l7_link", "zarm_r7_link", "zarm_r7_link"],
        "position_cost": 50.,
        "orientation_cost": 50.,
    },
    "head": {
        "smpl": ["neck", "head"],
        "robot": ["zhead_1_link", "zhead_2_link"],
        "position_cost": 200.,
        "orientation_cost": 50.,
    }
}