import os

from humanoid_retargeting.motion_player import AMASSPlayer
from humanoid_retargeting import AMASS_DATA_PATH

AMASS_FILE_PATH = os.path.join(AMASS_DATA_PATH, "ACCAD", 'Female1General_c3d', "A1_-_Stand_stageii.npz")


def test_plot():
    player = AMASSPlayer(source_file_path=AMASS_FILE_PATH, view=False)
    player.plot_ref_baselink_cartesian()
    player.plot_ref_baselink_quaternion()
    player.plot_ref_baselink_euler()
    player.plot_ref_joint_quaternion(joint_idx=0)


def test_lowpass_filter():
    player = AMASSPlayer(source_file_path=AMASS_FILE_PATH, view=False)
    player.lowpass_all_qpos()

def test_cali():
    player = AMASSPlayer(source_file_path=AMASS_FILE_PATH, view=False)
    player.load_cali_qpos()
