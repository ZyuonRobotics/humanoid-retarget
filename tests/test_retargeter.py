import os

from humanoid_retargeting import AMASS_DATA_PATH
from humanoid_retargeting.retargeter import Retargeter


def test_retargeter():
    AMASS_FILE_PATH = os.path.join(AMASS_DATA_PATH, "ACCAD", 'Female1General_c3d', "A11_-_crawl_forward_stageii.npz")

    retargeter = Retargeter(
        source_file_path=AMASS_FILE_PATH,
        robot_name="kuavo_s45",
        generator_type="smpl",
        params_name="try",
        view=False
    )
    retargeter.run_ik()
    retargeter.save_as_npy("test.npy", target_framerate=100)
    retargeter.save_as_csv("test.csv", target_framerate=100)
