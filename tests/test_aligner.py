from pathlib import Path

from humanoid_retargeting import SMPL_DATA_PATH
from humanoid_retargeting.aligner import Aligner

SMPL_FILE_PATH = Path(SMPL_DATA_PATH) / "ACCAD" / 'Female1Walking_c3d' / "B1_-_stand_to_walk_stageii.npz"


def test_aligner_default_config(tmp_path):
    aligner = Aligner(source_file_path=SMPL_FILE_PATH, generator_type="smpl",
                      robot_name="DumBot13-21dof", view=False)
    aligner.load_cali_qpos()
    aligner.save_retarget_config(str(tmp_path / "test"))


def test_aligner_load_config(tmp_path):
    aligner = Aligner(source_file_path=SMPL_FILE_PATH, generator_type="smpl",
                      robot_name="DumBot13-21dof", view=False, config_name="default")
    aligner.load_cali_qpos()
    aligner.save_retarget_config(str(tmp_path / "default"))


def test_aligner_offset_qpos():
    aligner = Aligner(source_file_path=SMPL_FILE_PATH, generator_type="smpl",
                      robot_name="DumBot13-21dof", view=False, config_name="default")
    aligner.load_cali_qpos()
    aligner.get_tracker_offset()
