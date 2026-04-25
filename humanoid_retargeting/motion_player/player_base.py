import time
from abc import ABC, abstractmethod

import numpy as np
import mujoco
import mujoco.viewer
from scipy.spatial.transform import Rotation
from hurodes.generators import MJCFGeneratorBase
import matplotlib.pyplot as plt

from humanoid_retargeting.utils.plot import plot2d


class MotionPlayerBase(ABC):
    generator_class = MJCFGeneratorBase
    file_suffix = ""

    def __init__(self, view=True):
        self.view = view

        self.generator: MJCFGeneratorBase = None
        self.create_generator()
        assert isinstance(self.generator, self.generator_class), "Generator is not of the correct type"

        self._viewer = None
        self._frame_rate: int = None
        self._ref_qpos: np.ndarray = None

        self._model = None
        self._data = None

        self.motion_data = None

        self._loaded = False


    def load(self, **kwargs):
        self._load(**kwargs)
        self.generator.load(**kwargs)
        self._loaded = True

    @classmethod
    def from_source_file_path(cls, source_file_path, **kwargs):
        player = cls(**kwargs)
        player.load(source_file_path=source_file_path)
        return player

    @property
    def model(self):
        assert self.generator is not None and self.generator.loaded, "Generator is not loaded"
        if self._model is None:
            self.generator.generate() # call generate() lazily, because it should not be called in load()
            self._model = mujoco.MjModel.from_xml_string(self.generator.xml_str) # type: ignore
        return self._model
    
    @property
    def data(self):
        assert self.generator is not None and self.generator.loaded, "Generator is not loaded"
        if self._data is None:
            self._data = mujoco.MjData(self.model) # type: ignore
        return self._data

    @abstractmethod
    def _load(self, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    def create_generator(self):
        raise NotImplementedError()

    @property
    def viewer(self):
        assert self._loaded, "Motion player is not loaded"
        assert self.view, "Viewer is not enabled"
        if self._viewer is None:
            self._viewer = mujoco.viewer.launch_passive(self.model, self.data)
        return self._viewer

    @property
    def ref_qpos(self) -> np.ndarray:
        assert self._loaded, "Motion player is not loaded"
        if self._ref_qpos is None:
            self.load()
        assert isinstance(self._ref_qpos, np.ndarray), "Reference qpos is not loaded"
        return self._ref_qpos

    @property
    def frame_rate(self) -> int:
        assert self._loaded, "Motion player is not loaded"
        if self._frame_rate is None:
            self.load_motion_file()
            assert isinstance(self._frame_rate, int), "Frame rate is not loaded"
        return self._frame_rate

    @property
    def frame_num(self):
        assert self._loaded, "Motion player is not loaded"
        return self.ref_qpos.shape[0]

    def sync_data(self, frame_idx):
        self.data.qpos[:] = self.ref_qpos[frame_idx]
        self.data.qvel[:] = 0
        mujoco.mj_forward(self.model, self.data) # type: ignore

    def render(self):
        assert self._loaded, "Motion player is not loaded"
        assert self.view, "Viewer is not enabled"

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

    def get_body_motion_data(self, body_names):
        """
        Play motion_data once and get position, orientation and velocity data for specified bodies

        Args:
            body_names (list): List of body names in the MuJoCo model

        Returns:
            dict: Dictionary containing position, orientation and velocity data for each body
                Format: {
                    'body_name1': {
                        'trans': numpy.ndarray,    # shape: (frame_num, 3) - translation (x, y, z) in world frame
                        'euler': numpy.ndarray,    # shape: (frame_num, 3) - euler angles (roll, pitch, yaw) in world frame
                        'lin_vel': numpy.ndarray,  # shape: (frame_num, 3) - linear velocity in body frame
                        'ang_vel': numpy.ndarray   # shape: (frame_num, 3) - angular velocity in body frame
                    },
                    ...
                }

        Note:
            - trans: Position of body origin in world coordinate system
            - euler: Orientation of body frame relative to world frame (world frame coordinates)
            - lin_vel: Linear velocity in body's local coordinate system
            - ang_vel: Angular velocity in body's local coordinate system

            The velocities are in body frame because MuJoCo's data.cvel provides velocities
            in the body's local coordinate system, which is more useful for analyzing body motion.
        """
        # Ensure motion data is loaded
        if self._ref_qpos is None:
            self.load_motion_file()

        # Validate body names exist
        for body_name in body_names:
            try:
                self.model.body(body_name)
            except KeyError:
                raise ValueError(f"Body '{body_name}' not found in the model")

        # Initialize result dictionary
        result = {}
        for body_name in body_names:
            result[body_name] = {
                'trans': np.zeros((self.frame_num, 3)),    # translation in world frame
                'euler': np.zeros((self.frame_num, 3)),    # euler angles in world frame (xyz)
                'lin_vel': np.zeros((self.frame_num, 3)),  # linear velocity in body frame
                'ang_vel': np.zeros((self.frame_num, 3))   # angular velocity in body frame
            }

        # Iterate through all frames
        for frame_idx in range(self.frame_num):
            # Sync data to current frame
            self.sync_data(frame_idx)

            # Get position, orientation and velocity for each body
            for body_name in body_names:
                body_id = self.model.body(body_name).id

                result[body_name]['trans'][frame_idx] = self.data.xpos[body_id].copy()
                result[body_name]['euler'][frame_idx] = Rotation.from_quat(self.data.xquat[body_id][[1, 2, 3, 0]]).as_euler('xyz')

        # Calculate linear and angular velocities based on position and orientation
        for body_name in body_names:
            result[body_name]['lin_vel'][:-1] = np.diff(result[body_name]['trans'], axis=0) * self.frame_rate
            euler_diff = np.diff(result[body_name]['euler'], axis=0)
            euler_diff[euler_diff > np.pi] -= 2*np.pi
            euler_diff[euler_diff < -np.pi] += 2*np.pi
            result[body_name]['ang_vel'][:-1] = euler_diff * self.frame_rate
        return result

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
