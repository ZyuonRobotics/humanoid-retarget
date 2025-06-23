import os

from hurodes import ROBOTS_PATH
import numpy as np
import matplotlib.pyplot as plt

from hurodes.mjcf_generator.unified_generator import UnifiedMJCFGenerator
from humanoid_retargeting.motion_player.player_base import MotionPlayerBase


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

class RobotSinePlayer(RobotMotionPlayer):
    def __init__(
            self,
                 robot_name,
                 view=True,
                 frame_rate=100,
                 max_steps=300000,
            stepping_period=0.7,
            joint_pos_scale=0.3
    ):
        super().__init__(source_file_path=None, robot_name=robot_name, view=view)

        self._frame_rate = frame_rate
        self.max_steps = max_steps
        self.stepping_period = stepping_period
        self.joint_pos_scale = joint_pos_scale

        self.stance_mask = None

    def load_motion_file(self):
        self._ref_qpos = np.zeros((self.max_steps, self.model.nq))

        time_idx = np.linspace(0, self.max_steps, num=self.max_steps) / self._frame_rate
        sine = np.sin(time_idx / self.stepping_period * 2 * np.pi)
        sin_left = np.where(sine > -0.1, 0, sine)
        sin_right = np.where(sine < 0.1, 0, sine)
        self._ref_qpos[:, 2] = self.data.qpos[2]

        # self._ref_qpos[:, 8] = self.joint_pos_scale * sin_left
        # self._ref_qpos[:, 11] = -2*self.joint_pos_scale  * sin_left
        # self._ref_qpos[:, 12] = self.joint_pos_scale* sin_left
        # self._ref_qpos[:, 18] = -self.joint_pos_scale * sine
        # self._ref_qpos[:, 21] = -2 * self.joint_pos_scale * sin_right
        #
        # self._ref_qpos[:, 13] = -self.joint_pos_scale * sin_right
        # self._ref_qpos[:, 16] = 2 * self.joint_pos_scale * sin_right
        # self._ref_qpos[:, 17] = -self.joint_pos_scale * sin_right
        # self._ref_qpos[:, 22] = self.joint_pos_scale * sine
        # self._ref_qpos[:, 25] = 2 * self.joint_pos_scale * sin_left

        self._ref_qpos[:, 7] = self.joint_pos_scale * sin_left
        self._ref_qpos[:, 10] = -2*self.joint_pos_scale  * sin_left
        self._ref_qpos[:, 11] = self.joint_pos_scale* sin_left


        self._ref_qpos[:, 13] = -self.joint_pos_scale * sin_right
        self._ref_qpos[:, 16] = 2 * self.joint_pos_scale * sin_right
        self._ref_qpos[:, 17] = -self.joint_pos_scale * sin_right

        self._ref_qpos[:, 25] = 1
        self._ref_qpos[:, 32] = 1


        self.stance_mask = np.zeros((self.max_steps, 2))
        self.stance_mask[:, 0] = sine >= 0
        self.stance_mask[:, 1] = sine < 0
        self.stance_mask[sine < 0.1] = 1

    def plot_stance(self):
        if self.ref_qpos is None:
            self.load_motion_file()

        foot_height = np.zeros((self.frame_num, 2))
        for frame_idx in range(self.frame_num):
            self.sync_data(frame_idx)
            foot_height[frame_idx, 0] = self.data.xpos[self.model.body("leg_l5_link").id, 2]
            foot_height[frame_idx, 1] = self.data.xpos[self.model.body("leg_r5_link").id, 2]

        plt.plot(foot_height[:, 0], label="left")
        plt.plot(foot_height[:, 1], label="right")
        plt.plot(self.stance_mask[:, 0], label="left_mask")
        plt.plot(self.stance_mask[:, 1], label="right_mask")
        plt.legend()
        plt.show()

if __name__ == '__main__':
    player = RobotSinePlayer(robot_name="unitree_g1")
    player.render()
    player.close()

    # player.plot_stance()
