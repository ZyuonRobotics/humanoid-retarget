import time
from abc import ABC, abstractmethod

import mujoco
import mujoco.viewer
from scipy.spatial.transform import Rotation
from hurodes.mjcf_generator.generator_base import MJCFGeneratorBase

from humanoid_retargeting.utils.plot import plot2d


class MotionPlayerBase(ABC):
    generator_class = MJCFGeneratorBase
    file_suffix = ""

    def __init__(self, source_file_path, view=True):
        self.source_file_path = source_file_path
        self.view = view

        self.generator:MJCFGeneratorBase = None
        self.create_generator()
        self.generator.build()

        self.model = mujoco.MjModel.from_xml_string(self.generator.mjcf_str)
        self.data = mujoco.MjData(self.model)
        self.motion_data = None

        self._viewer = None
        self._frame_rate = None
        self._ref_qpos = None

    @abstractmethod
    def create_generator(self):
        raise NotImplementedError()

    @property
    def viewer(self):
        if self._viewer is None:
            self._viewer = mujoco.viewer.launch_passive(self.model, self.data)
        return self._viewer

    @property
    def ref_qpos(self):
        if self._ref_qpos is None:
            self.load_motion_file()
        return self._ref_qpos

    @property
    def frame_rate(self):
        if self._frame_rate is None:
            self.load_motion_file()
        return self._frame_rate

    @property
    def frame_num(self):
        return self.ref_qpos.shape[0]

    @abstractmethod
    def load_motion_file(self):
        raise NotImplemented

    def sync_data(self, frame_idx):
        self.data.qpos[:] = self.ref_qpos[frame_idx]
        self.data.qvel[:] = 0
        mujoco.mj_forward(self.model, self.data)

    def render(self):
        assert self.view, "Viewer is not enabled"
        if self.ref_qpos is None:
            self.load_motion_file()

        for frame_idx in range(self.frame_num):
            step_start = time.time()

            self.sync_data(frame_idx)
            self.viewer.sync()

            time_until_next_step = 1 / self.frame_rate - (time.time() - step_start)
            if time_until_next_step > 0:
                time.sleep(time_until_next_step)

        self.close()

    def plot_ref_baselink_cartesian(self):
        plot2d(self.ref_qpos[:, :3], ["x", "y", "z"], view=self.view)

    def plot_ref_baselink_quaternion(self):
        plot2d(self.ref_qpos[:, 3:7], ["w", "x", "y", "z"], view=self.view)

    def plot_ref_baselink_euler(self):
        euler_pos = Rotation.from_quat(self.ref_qpos[:, [4, 5, 6, 3]]).as_euler("xyz")
        plot2d(euler_pos, ["roll", "pitch", "yaw"], view=self.view)

    def plot_ref_joint_quaternion(self, joint_idx=0):
        assert joint_idx + 1 < self.model.njnt, "Invalid joint index"
        assert self.model.joint(joint_idx + 1).type[0] == 1, f"Joint type of {joint_idx} is not ball"
        plot2d(
            array=self.ref_qpos[:, 7 + joint_idx * 4: 7 + (joint_idx + 1) * 4],
            dim_label=["w", "x", "y", "z"],
            view=self.view
        )

    def close(self):
        if self.view:
            self.viewer.close()
