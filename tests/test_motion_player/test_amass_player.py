import os

from humanoid_retargeting import AMASS_DATA_PATH
from humanoid_retargeting.motion_player import AMASSPlayer

AMASS_FILE_PATH = os.path.join(AMASS_DATA_PATH, "ACCAD", 'Female1Walking_c3d', "B1_-_stand_to_walk_stageii.npz")


def test_plot():
    player = AMASSPlayer(source_file_path=AMASS_FILE_PATH, view=False)
    player.plot_ref_baselink_cartesian()
    player.plot_ref_baselink_quaternion()
    player.plot_ref_baselink_euler()
    player.plot_ref_joint_quaternion(joint_idx=0)


def test_lowpass_filter():
    player = AMASSPlayer(source_file_path=AMASS_FILE_PATH, view=False)
    player.load_motion_file()
    player.lowpass_all_qpos()

def test_frame_rate():
    player = AMASSPlayer(source_file_path=AMASS_FILE_PATH, view=False)
    assert isinstance(player.frame_rate, int)
