from abc import ABC, abstractmethod
import time

import mujoco
import mujoco.viewer
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.signal import butter, filtfilt
import matplotlib.pyplot as plt

from humanoid_retargeting.mjcf_generator.generator_base import RetargetingMJCFGenerator


def plot_data(array, dim_label=None):
    if dim_label is None:
        dim_label = [f"dim{i}" for i in range(array.shape[1])]
    for i, label in zip(range(array.shape[1]), dim_label):
        plt.plot(array[:, i], label=label)
    plt.legend()
    plt.show()


class MotionPlayerBase(ABC):
    generator_class = RetargetingMJCFGenerator

    def __init__(self, source_file_path, cali_info=None, view=True):
        self.source_file_path = source_file_path
        self.cali_info = cali_info
        self.view = view

        self.generator = self.generator_class(source_file_path=source_file_path)
        self.generator.build()

        self.mujoco_model = mujoco.MjModel.from_xml_string(self.generator.mjcf_str)
        self.mujoco_data = mujoco.MjData(self.mujoco_model)
        self.motion_data = None

        self._viewer = None
        self._frame_rate = None
        self._ref_qpos = None
        self._cali_qpos = None

    @property
    def viewer(self):
        if self._viewer is None:
            self._viewer = mujoco.viewer.launch_passive(self.mujoco_model, self.mujoco_data)
        return self._viewer

    @property
    def ref_qpos(self):
        if self._ref_qpos is None:
            self.load_motion_file()
        return self._ref_qpos

    @property
    def cali_qpos(self):
        if self._cali_qpos is None:
            self.load_cali_qpos()
        return self._cali_qpos

    @property
    def frame_rate(self):
        if self._frame_rate is None:
            self.load_motion_file()
        return self._frame_rate

    @abstractmethod
    def load_motion_file(self):
        raise NotImplemented

    @abstractmethod
    def load_cali_qpos(self):
        raise NotImplemented

    def render(self):
        assert self.view, "Viewer is not enabled"
        if self.ref_qpos is None:
            self.load_motion_file()

        for i in range(self.ref_qpos.shape[0]):
            step_start = time.time()

            self.mujoco_data.qpos[:] = self.ref_qpos[i]
            self.mujoco_data.qvel[:] = 0
            mujoco.mj_forward(self.mujoco_model, self.mujoco_data)
            self.viewer.sync()

            time_until_next_step = 1 / self.frame_rate - (time.time() - step_start)
            if time_until_next_step > 0:
                time.sleep(time_until_next_step)

        self.close()

    def plot_ref_baselink_cartesian(self):
        plot_data(self.ref_qpos[:, :3], ["x", "y", "z"])

    def plot_ref_baselink_quaternion(self):
        plot_data(self.ref_qpos[:, 3:7], ["w", "x", "y", "z"])

    def plot_ref_baselink_euler(self):
        euler_pos = Rotation.from_quat(self.ref_qpos[:, [4, 5, 6, 3]]).as_euler("xyz")
        plot_data(euler_pos, ["roll", "pitch", "yaw"])

    def plot_ref_joint_quaternion(self, joint_idx=0):
        assert joint_idx + 1 < self.mujoco_model.njnt, "Invalid joint index"
        assert self.mujoco_model.joint(joint_idx + 1).type[0] == 1, f"Joint type of {joint_idx} is not ball"
        plot_data(self.ref_qpos[:, 7 + joint_idx * 4: 7 + (joint_idx + 1) * 4], ["w", "x", "y", "z"])

    def lowpass(self, data, cutoff=20, order=2):
        nyq = 0.5 * self.frame_rate
        normal_cutoff = cutoff / nyq
        b, a = butter(order, normal_cutoff, btype='low', analog=False)
        filtered = np.zeros_like(data)
        for i in range(data.shape[1]):
            filtered[:, i] = filtfilt(b, a, data[:, i])
        return filtered

    def lowpass_quaternion(self, quat, cutoff=20, order=2):
        rotvec = Rotation.from_quat(quat[:, [1, 2, 3, 0]]).as_rotvec()
        lowpass_filter_rotvec = self.lowpass(rotvec, cutoff, order)
        filtered_quat = Rotation.from_rotvec(lowpass_filter_rotvec).as_quat()[:, [3, 0, 1, 2]]
        return filtered_quat

    def lowpass_all_qpos(self, cutoff=20, order=2):
        for joint_idx in range(self.mujoco_model.njnt):
            if joint_idx == 0:
                assert self.mujoco_model.joint(0).type[0] == 0, "Root joint should be free"
                self._ref_qpos[:, :3] = self.lowpass(self.ref_qpos[:, :3], cutoff, order)
            else:
                assert self.mujoco_model.joint(joint_idx).type[0] == 1, f"Joint type of {joint_idx} is not ball"
            quat = self.ref_qpos[:, 3 + joint_idx * 4: 3 + (joint_idx + 1) * 4]
            res_quat = self.lowpass_quaternion(quat, cutoff, order)
            self._ref_qpos[:, 3 + joint_idx * 4: 3 + (joint_idx + 1) * 4] = res_quat

    def render_cali(self):
        assert self.view, "Viewer is not enabled"
        if self.cali_qpos is None:
            self.load_cali_qpos()

        while True:
            self.mujoco_data.qpos[:] = self.cali_qpos
            self.mujoco_data.qvel[:] = 0

            mujoco.mj_forward(self.mujoco_model, self.mujoco_data)
            self.viewer.sync()


    def close(self):
        if self.view:
            self.viewer.close()

