from pathlib import Path

from humanoid_retargeting import SMPL_DATA_PATH
from humanoid_retargeting.retargeter import Retargeter


def test_retargeter(tmp_path):
    SMPL_FILE_PATH = Path(SMPL_DATA_PATH) / "ACCAD" / 'Female1Walking_c3d' / "B1_-_stand_to_walk_stageii.npz"

    retargeter = Retargeter(
        source_file_path=SMPL_FILE_PATH,
        robot_name="kuavo_s45",
        generator_type="smpl",
        params_name="default",
        view=False
    )
    retargeter.run_ik()
    retargeter.save_as_npz(str(tmp_path / "test.npy"), target_framerate=100)
    retargeter.save_as_csv(str(tmp_path / "test.csv"), target_framerate=100)
