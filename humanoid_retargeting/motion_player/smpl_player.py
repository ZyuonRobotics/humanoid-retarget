import numpy as np
from scipy.spatial.transform import Rotation

from humanoid_retargeting.mjcf_generator.smpl2mjcf_generator import SMPL2MJCFGenerator, SMPLH_JOINT_NAMES
from humanoid_retargeting.motion_player.humanoid_player_base import HumanoidMotionPlayerBase


class SMPLPlayer(HumanoidMotionPlayerBase):
    generator_class = SMPL2MJCFGenerator
    file_suffix = "npz"

    def __init__(self, view=True, global_body_ratio=1.0, relative_body_ratio_dict=None):
        super().__init__(view=view, global_body_ratio=global_body_ratio, relative_body_ratio_dict=relative_body_ratio_dict)
        self.smpl_type = "smpl"


    def get_frame_rate(self) -> int:
        if "mocap_frame_rate" in self.motion_data:
            frame_rate = self.motion_data["mocap_frame_rate"]
        elif "mocap_framerate" in self.motion_data:
            frame_rate = self.motion_data["mocap_framerate"]
        else:
            raise ValueError(f"mocap_frame_rate not found in {self.source_file_path}")
        return int(frame_rate)

    @staticmethod
    def rotvec2quat(rotvec):
        # rotvec to quat (w, x, y, z)
        rotations = Rotation.from_rotvec(rotvec)
        quat = rotations.as_quat()
        return np.roll(quat, shift=1, axis=1)

    def get_qpos(self):
        frame_num = self.motion_data['poses'].shape[0]
        rotvec_all = self.motion_data['poses'].reshape([frame_num, -1, 3])

        pelvis_offset = self.model.body("pelvis").pos[[1, 2, 0]]
        pelvis_offset /= self.global_body_ratio

        trans = self.motion_data['trans'] + pelvis_offset
        rotvec_all[:, 1:, :] = rotvec_all[:, 1:, [2, 0, 1]]

        ref_qpos = np.zeros([trans.shape[0], self.model.nq])
        ref_qpos[:, 0:3] = trans
        mat = 0.5 * np.array([[1, -1, -1, -1], [1, 1, 1, -1], [1, -1, 1, 1], [1, 1, -1, 1]])
        ref_qpos[:, 3:7] = self.rotvec2quat(rotvec_all[:, 0]) @ mat
        for joint_id in range(1, len(self.generator.joint_names)):
            joint_idx = self.model.body(self.generator.joint_names[joint_id]).jntadr[0]
            joint_qposadr = self.model.joint(joint_idx).qposadr[0]
            ref_qpos[:, joint_qposadr:joint_qposadr + 4] = self.rotvec2quat(rotvec_all[:, joint_id])

        return ref_qpos

    def _load(self, source_file_path):
        self.motion_data = np.load(source_file_path)
        assert "poses" in self.motion_data

        self._frame_rate = self.get_frame_rate()
        self._ref_qpos = self.get_qpos()

    @property
    def foot_names(self):
        """Return default foot names for SMPL model"""
        return ["left_foot", "right_foot"]

    @property
    def hip_names(self):
        """Return default hip names for SMPL model"""
        return ["left_hip", "right_hip"]
