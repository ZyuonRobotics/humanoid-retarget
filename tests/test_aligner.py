import os

from humanoid_retargeting import AMASS_DATA_PATH
from humanoid_retargeting.aligner import Aligner

AMASS_FILE_PATH = os.path.join(AMASS_DATA_PATH, "ACCAD", 'Female1Walking_c3d', "B1_-_stand_to_walk_stageii.npz")


def test_aligner_default_params():
    aligner = Aligner(source_file_path=AMASS_FILE_PATH, generator_type="smpl",
                      robot_name="kuavo_s45", view=False)
    aligner.load_cali_qpos()
    aligner.save_retarget_params("test")


def test_aligner_load_params():
    aligner = Aligner(source_file_path=AMASS_FILE_PATH, generator_type="smpl",
                      robot_name="kuavo_s45", view=False, params_name="default")
    aligner.load_cali_qpos()
    aligner.save_retarget_params("default")


def test_aligner_offset_qpos():
    aligner = Aligner(source_file_path=AMASS_FILE_PATH, generator_type="smpl",
                      robot_name="kuavo_s45", view=False, params_name="default")
    aligner.load_cali_qpos()
    aligner.get_tracker_offset()
