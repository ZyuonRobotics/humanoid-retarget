from pathlib import Path

from humanoid_retargeting import SMPL_DATA_PATH
from humanoid_retargeting.aligner import Aligner

SMPL_FILE_PATH = Path(SMPL_DATA_PATH) / "ACCAD" / 'Female1Walking_c3d' / "B1_-_stand_to_walk_stageii.npz"


def test_aligner_default_params(tmp_path):
    aligner = Aligner(source_file_path=SMPL_FILE_PATH, generator_type="smpl",
                      robot_name="kuavo_s45", view=False)
    aligner.load_cali_qpos()
    aligner.save_retarget_params(str(tmp_path / "test"))


def test_aligner_load_params(tmp_path):
    aligner = Aligner(source_file_path=SMPL_FILE_PATH, generator_type="smpl",
                      robot_name="kuavo_s45", view=False, params_name="default")
    aligner.load_cali_qpos()
    aligner.save_retarget_params(str(tmp_path / "default"))


def test_aligner_offset_qpos():
    aligner = Aligner(source_file_path=SMPL_FILE_PATH, generator_type="smpl",
                      robot_name="kuavo_s45", view=False, params_name="default")
    aligner.load_cali_qpos()
    aligner.get_tracker_offset()
