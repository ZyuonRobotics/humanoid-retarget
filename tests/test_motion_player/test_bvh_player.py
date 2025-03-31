import os

from humanoid_retargeting.motion_player import BVHPlayer
from humanoid_retargeting import BVH_DATA_PATH

BVH_FILE_PATH = os.path.join(BVH_DATA_PATH, "Reallusion", "newtaichi", '1_Skill.bvh')


def test_plot():
    player = BVHPlayer(source_file_path=BVH_FILE_PATH, view=False)
    player.plot_ref_baselink_cartesian()
    player.plot_ref_baselink_quaternion()
    player.plot_ref_baselink_euler()
    player.plot_ref_joint_quaternion(joint_idx=0)


def test_lowpass_filter():
    player = BVHPlayer(source_file_path=BVH_FILE_PATH)
    player.lowpass_all_qpos()

def test_cali():
    player = BVHPlayer(source_file_path=BVH_FILE_PATH)
    player.load_cali_qpos()
