from pathlib import Path
import mujoco

from hurodes import ROBOTS_PATH
import numpy as np
import matplotlib.pyplot as plt

from hurodes.generators import MJCFHumanoidGenerator
from humanoid_retargeting.motion_player.player_base import MotionPlayerBase


class RobotMotionPlayer(MotionPlayerBase):
    generator_class = MJCFHumanoidGenerator
    file_suffix = "npz"

    def __init__(self, robot_name, view=True):
        self.robot_name = robot_name

        super().__init__(view=view)

    @property
    def model(self):
        assert self.generator is not None and self.generator.loaded, "Generator is not loaded"
        if self._model is None:
            self.generator.generate(relative_mesh_path=False)
            self._model = mujoco.MjModel.from_xml_string(self.generator.xml_str)
        return self._model

    def create_generator(self):
        self.generator = self.generator_class()

    def load_motion_file(self, source_file_path):
        motion_dict = np.load(source_file_path)

        self._frame_rate = motion_dict["frame_rate"]
        self._ref_qpos = np.concatenate([
            motion_dict["root_trans"],
            motion_dict["root_quat"],
            motion_dict["joint_pos"]
        ], axis=1)

    def _load(self, source_file_path, **kwargs):
        self.load_motion_file(source_file_path)

    def get_all_frame_body_transforms(self) -> dict:
        """Pre-compute all body transforms for every frame.

        Returns:
            dict: Contains 'xpos' (frame_num, nbody, 3) and 'xquat' (frame_num, nbody, 4)
        """
        if self._ref_qpos is None:
            self.load_motion_file()

        nbody = self.model.nbody
        frame_num = self.frame_num

        xpos = np.zeros((frame_num, nbody, 3))
        xquat = np.zeros((frame_num, nbody, 4))

        for frame_idx in range(frame_num):
            self.data.qpos[:] = self._ref_qpos[frame_idx]
            self.data.qvel[:] = 0
            mujoco.mj_forward(self.model, self.data)

            xpos[frame_idx] = self.data.xpos.copy()
            xquat[frame_idx] = self.data.xquat.copy()

        return {
            "xpos": xpos.tolist(),
            "xquat": xquat.tolist()
        }
