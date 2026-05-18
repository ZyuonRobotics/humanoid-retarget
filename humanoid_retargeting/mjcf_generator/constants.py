BODY_JOINT_NAMES = [
    'pelvis',
    'left_hip',
    'right_hip',
    'spine1',
    'left_knee',
    'right_knee',
    'spine2',
    'left_ankle',
    'right_ankle',
    'spine3',
    'left_foot',
    'right_foot',
    'neck',
    'left_collar',
    'right_collar',
    'head',
    'left_shoulder',
    'right_shoulder',
    'left_elbow',
    'right_elbow',
    'left_wrist',
    'right_wrist',
]

FINGER_JOINT_NAMES = [
    'left_index1',
    'left_index2',
    'left_index3',
    'left_middle1',
    'left_middle2',
    'left_middle3',
    'left_pinky1',
    'left_pinky2',
    'left_pinky3',
    'left_ring1',
    'left_ring2',
    'left_ring3',
    'left_thumb1',
    'left_thumb2',
    'left_thumb3',
    'right_index1',
    'right_index2',
    'right_index3',
    'right_middle1',
    'right_middle2',
    'right_middle3',
    'right_pinky1',
    'right_pinky2',
    'right_pinky3',
    'right_ring1',
    'right_ring2',
    'right_ring3',
    'right_thumb1',
    'right_thumb2',
    'right_thumb3',
]

SIMPLE_HAND_JOINT_NAMES = [
    'left_hand',
    'right_hand',
]

SMPL_JOINT_NAMES = BODY_JOINT_NAMES + SIMPLE_HAND_JOINT_NAMES
SMPLH_JOINT_NAMES = BODY_JOINT_NAMES + FINGER_JOINT_NAMES

# SMPL/SMPLH joint hierarchy (kintree_table)
# Standard SMPL joint parent structure
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