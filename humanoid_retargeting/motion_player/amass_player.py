import time

import numpy as np
import mujoco
from scipy.spatial.transform import Rotation

from humanoid_retargeting.motion_player.player_base import MotionPlayerBase
from humanoid_retargeting.mjcf_generator.smpl2mjcf import SMPL2MJCFGenerator, SMPLH_JOINT_NAMES


TRACKER_DICT = {
    "upper_base": {
        "smpl": ["left_collar", "right_collar"],
        "robot": ["base_link", "base_link"],
        "position_cost": 100.,
        "orientation_cost": 50.,
    },
    "lower_base": {
        "smpl": ["left_hip", "right_hip"],
        "robot": ["base_link", "base_link"],
        "position_cost": 100.,
        "orientation_cost": 50.,
    },
    "leg": {
        "smpl": ["left_knee", "left_ankle", "right_knee", "right_ankle"],
        "robot": ["leg_l4_link", "leg_l6_link", "leg_r4_link", "leg_r6_link"],
        "position_cost": 100.,
        "orientation_cost": 50.,
    },
    "foot": {
        "smpl": ["left_foot", "right_foot"],
        "robot": ["leg_l6_link", "leg_r6_link"],
        "position_cost": 200.,
        "orientation_cost": 50.,
    },
    "arm": {
        "smpl": ["left_elbow", "left_elbow", "right_elbow", "right_elbow"],
        "robot": ["zarm_l3_link", "zarm_l6_link", "zarm_r3_link", "zarm_r6_link"],
        "position_cost": 100.,
        "orientation_cost": 0.,
    },
    "hand": {
        "smpl": ["left_wrist", "right_wrist"],
        "robot": ["zarm_l5_link", "zarm_r5_link"],
        "position_cost": 100.,
        "orientation_cost": 0.,
    },
    "finger": {
        "smpl": ["left_index1", "left_pinky1", "right_index1", "right_pinky1"],
        "robot": ["zarm_l7_link", "zarm_l7_link", "zarm_r7_link", "zarm_r7_link"],
        "position_cost": 50.,
        "orientation_cost": 50.,
    },
    "head": {
        "smpl": ["neck", "head"],
        "robot": ["zhead_1_link", "zhead_2_link"],
        "position_cost": 200.,
        "orientation_cost": 50.,
    }
}

class AmassPlayer(MotionPlayerBase):
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

    def load_cali_qpos(self):
        self._cali_qpos = np.zeros(self.mujoco_model.nq)
        self._cali_qpos[3] = 1
        self.mujoco_data.qpos[:] = self._cali_qpos
        mujoco.mj_forward(self.mujoco_model, self.mujoco_data)

        foot_z = (self.mujoco_data.body("left_foot").xpos[2] + self.mujoco_data.body("left_foot").xpos[2]) / 2.
        self._cali_qpos[2] -= foot_z

    def load_motion_file(self):
        self.motion_data = np.load(self.source_file_path)
        assert "poses" in self.motion_data

        self._frame_rate = self.get_frame_rate()
        self._ref_qpos = self.get_qpos()

    #     self.adjust_z_offset()
    #
    # def adjust_z_offset(self):
    #     z_list = []
    #
    #     last_lowest_z = 0
    #     for frame_id in range(self.ref_qpos.shape[0]):
    #         self.mujoco_data.qpos[:] = self.ref_qpos[frame_id, :]
    #         mujoco.mj_forward(self.mujoco_model, self.mujoco_data)
    #
    #         lowest_z = np.inf
    #         for body_name in ["left_ankle", "right_ankle"]:
    #             lowest_z = min(lowest_z, self.mujoco_data.body(body_name).xpos[2])
    #         if abs(last_lowest_z - lowest_z) * self.frame_rate < 0.01 and lowest_z != np.inf:
    #             z_list.append(lowest_z)
    #         last_lowest_z = lowest_z
    #     offset_z = 0 if len(z_list) == 0 else (np.mean(z_list) - 0.05)
    #     print("offset_z: ", offset_z)
    #     self.ref_qpos[:, 2] -= offset_z


if __name__ == '__main__':
    import os.path as osp

    import mujoco
    import mujoco.viewer

    from humanoid_retargeting import AMASS_DATA_PATH

    amass_file_path = osp.join(AMASS_DATA_PATH, "amass", 'CMU', "12", "4_tai_chi_stageii.npz")

    player = AmassPlayer(source_file_path=amass_file_path)
    player.lowpass_all_qpos(cutoff=5)
    player.render()
    # player.render_cali()
