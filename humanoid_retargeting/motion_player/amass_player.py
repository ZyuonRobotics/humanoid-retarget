import time

import numpy as np
import mujoco
from scipy.spatial.transform import Rotation

from humanoid_retargeting.motion_player.player_base import MotionPlayerBase
from humanoid_retargeting.mjcf_generator.smpl2mjcf import SMPL2MJCFGenerator, SMPLH_JOINT_NAMES

class AMASSPlayer(MotionPlayerBase):
    generator_class = SMPL2MJCFGenerator

    def __init__(self, source_file_path, view=True):
        super().__init__(source_file_path=source_file_path, view=view)

    def get_frame_rate(self):
        if "mocap_frame_rate" in self.motion_data:
            frame_rate = self.motion_data["mocap_frame_rate"]
        elif "mocap_framerate" in self.motion_data:
            frame_rate = self.motion_data["mocap_framerate"]
        else:
            raise ValueError("Invalid npz file")
        return frame_rate

    @staticmethod
    def rotvec2quat(rotvec):
        # rotvec to quat (w, x, y, z)
        rotations = Rotation.from_rotvec(rotvec)
        quat = rotations.as_quat()
        return np.roll(quat, shift=1, axis=1)

    def get_qpos(self):
        root_orient = self.motion_data['poses'][:, :3]
        pose_body = self.motion_data['poses'][:, 3:66]
        pose_hand = self.motion_data['poses'][:, 66:52 * 3]
        rotvec_all = np.hstack([root_orient, pose_body, pose_hand]).reshape([-1, 52, 3])
        trans = self.motion_data['trans'] + self.mujoco_model.body("pelvis").pos[[1, 2, 0]]
        rotvec_all[:, 1:, :] = rotvec_all[:, 1:, [2, 0, 1]]

        ref_qpos = np.zeros([trans.shape[0], self.mujoco_model.nq])
        ref_qpos[:, 0:3] = trans
        mat = 0.5 * np.array([[1, -1, -1, -1], [1, 1, 1, -1], [1, -1, 1, 1], [1, 1, -1, 1]])
        ref_qpos[:, 3:7] = self.rotvec2quat(rotvec_all[:, 0]) @ mat
        for joint_id in range(1, 52):
            joint_qposadr = self.mujoco_model.joint(self.mujoco_model.body(SMPLH_JOINT_NAMES[joint_id]).jntadr[0]).qposadr[0]
            ref_qpos[:, joint_qposadr:joint_qposadr + 4] = self.rotvec2quat(rotvec_all[:, joint_id])

        return ref_qpos

    def load_motion_file(self):
        self.motion_data = np.load(self.source_file_path)
        assert "poses" in self.motion_data

        self._frame_rate = self.get_frame_rate()
        self._ref_qpos = self.get_qpos()


if __name__ == '__main__':
    import os
    from humanoid_retargeting import AMASS_DATA_PATH

    AMASS_FILE_PATH = os.path.join(AMASS_DATA_PATH, "ACCAD", 'Female1General_c3d', "A11_-_crawl_forward_stageii.npz")

    player = AMASSPlayer(source_file_path=AMASS_FILE_PATH)
    player.render()
