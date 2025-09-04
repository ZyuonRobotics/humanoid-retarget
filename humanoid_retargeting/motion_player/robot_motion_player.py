from pathlib import Path

from hurodes import ROBOTS_PATH
import numpy as np
import matplotlib.pyplot as plt

from hurodes.generators import MJCFHumanoidGenerator
from humanoid_retargeting.motion_player.player_base import MotionPlayerBase


class RobotMotionPlayer(MotionPlayerBase):
    generator_class = MJCFHumanoidGenerator
    file_suffix = "npz"

    def __init__(self, source_file_path, robot_name, view=True):
        self.robot_name = robot_name

        super().__init__(source_file_path=source_file_path, view=view)


    def create_generator(self):
        self._generator = self.generator_class(Path(ROBOTS_PATH) / self.robot_name, disable_gravity=True)

    def load_motion_file(self):
        motion_dict = np.load(self.source_file_path)

        self._frame_rate = motion_dict["frame_rate"]
        self._ref_qpos = np.concatenate([
            motion_dict["root_trans"],
            motion_dict["root_quat"][:, [3, 0, 1, 2]],
            motion_dict["joint_pos"]
        ], axis=1)
