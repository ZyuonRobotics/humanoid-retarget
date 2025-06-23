import os

from hurodes import ROBOTS_PATH
import numpy as np

from hurodes.mjcf_generator.unified_generator import UnifiedMJCFGenerator
from humanoid_retargeting.motion_player.player_base import MotionPlayerBase
from humanoid_retargeting.utils.lowpass import filter_lowpass2d, filter_lowpass_quaternion


class RobotMotionPlayer(MotionPlayerBase):
    generator_class = UnifiedMJCFGenerator
    file_suffix = "npy"

    def __init__(self, source_file_path, robot_name, view=True):
        self.robot_name = robot_name

        super().__init__(source_file_path=source_file_path, view=view)


    def create_generator(self):
        self.generator = self.generator_class(os.path.join(ROBOTS_PATH, self.robot_name), disable_gravity=True)

    def load_motion_file(self):
        motion_dict = np.load(self.source_file_path, allow_pickle=True).item()

        self._frame_rate = motion_dict["frame_rate"]
        self._ref_qpos = np.concatenate([
            motion_dict["root_trans"],
            motion_dict["root_quat"][:, [3, 0, 1, 2]],
            motion_dict["joint_pos"]
        ], axis=1)

if __name__ == '__main__':
    player = RobotMotionPlayer("../taichi.npy", robot_name="kuavo_s45")
    player.render()
    player.close()
