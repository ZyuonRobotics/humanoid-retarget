from collections import defaultdict
import os.path as osp

import numpy as np
import mujoco
import mujoco.viewer
from scipy.spatial.transform import Rotation

from humanoid_retargeting.mjcf_generator.bvh2mjcf import BVH2MJCFGenerator
from humanoid_retargeting.motion_player.player_base import MotionPlayerBase
from humanoid_retargeting import BVH_DATA_PATH

CC3PLUS_CALI_QUAT = [
    [1., 0.1, 0., 0.],
    [0.01, 0., 0.09, 1.],
    [1., -0.01, 0., 0.],
    [0.79, 0.62, -0.04, 0.04],
    [0.98, 0.18, 0.03, -0.03],
    [0.98, 0.18, 0.03, -0.03],
    [0.98, -0.19, 0.03, -0.02],
    [0.97, -0.23, 0.05, 0.],
    [0.99, -0.15, 0.04, 0.01],
    [0.99, -0.16, 0.04, 0.01],
    [1., -0.03, 0., 0.01],
    [1., 0., 0., 0.],
    [1., 0., 0., 0.],
    [1., 0., 0.02, 0.],
    [1., 0., 0., 0.],
    [1., 0., 0., 0.],
    [0.01, 0., -0.09, -1.],
    [1., -0.01, 0., 0.],
    [1., 0., -0.02, 0.],
    [0.79, 0.62, 0.04, -0.04],
    [0.98, 0.18, -0.03, 0.03],
    [1., -0.03, 0., -0.01],
    [0.98, -0.19, -0.03, 0.02],
    [0.97, -0.23, -0.05, 0.],
    [0.99, -0.16, -0.04, -0.01],
    [0.99, -0.15, -0.04, -0.01],
    [0.98, 0.18, -0.03, 0.03],
    [1., 0., 0., 0.],
    [1., 0., 0., 0.],
    [1., 0., 0., 0.],
    [1., 0., 0., 0.],
    [0.99, 0.12, 0., 0.],
    [0.99, -0.16, 0., 0.],
    [1., -0.06, 0., 0.],
    [0.98, 0.2, 0., 0.],
    [1., 0.01, 0., 0.],
    [0.99, -0.12, 0., 0.],
    [0.5, 0.5, 0.5, 0.5],
    [0.71, 0., 0., 0.71],
    [1., 0., 0., 0.05],
    [1., 0., 0., 0.08],
    [1., 0., 0., 0.],
    [0., -1., 0., 0.],
    [0., 0.71, 0., 0.71],
    [0., 0.71, 0., 0.71],
    [0.71, 0., 0., 0.71],
    [0., 1., 0., 0.],
    [0.7, -0.01, 0.15, -0.7],
    [0.99, 0.10, 0.05, 0.],
    [1., 0.01, 0., 0.],
    [1., 0., 0., 0.],
    [1., 0., 0., 0.],
    [1., 0., 0., 0.],
    [1., -0.06, 0., 0.02],
    [1., 0.06, 0., -0.01],
    [1., 0., 0., -0.02],
    [1., -0.02, 0., 0.05],
    [1., 0.06, 0., -0.01],
    [1., -0.01, 0., -0.03],
    [1., -0.01, 0., 0.04],
    [1., 0.06, 0., -0.02],
    [1., 0., 0., -0.01],
    [1., 0., 0., 0.02],
    [1., 0.05, 0., -0.02],
    [1., 0.01, 0.01, -0.01],
    [1., 0.02, 0., 0.03],
    [0.89, 0.44, -0.12, -0.07],
    [0.99, -0.16, 0., 0.05],
    [1., 0., 0., 0.04],
    [1., 0., 0., 0.],
    [1., 0., 0., 0.],
    [0., 0., 0.64, 0.77],
    [1., 0., 0., 0.],
    [0., 0., 0.64, 0.77],
    [1., 0., 0., 0.],
    [0.7, -0.01, -0.15, 0.7],
    [0.99, 0.10, -0.06, 0.01],
    [1., 0.01, 0., 0.],
    [1., 0., 0., 0.],
    [1., 0., 0., 0.],
    [1., 0., 0., 0.],
    [1., -0.06, 0., -0.02],
    [1., 0.06, 0., 0.01],
    [1., -0.01, 0., 0.03],
    [1., -0.01, 0., -0.04],
    [1., 0.06, 0., 0.02],
    [1., 0., 0., 0.01],
    [1., 0., 0., -0.02],
    [0.89, 0.44, 0.12, 0.07],
    [0.99, -0.16, 0., -0.05],
    [1., 0., 0., -0.04],
    [1., 0.05, 0., 0.02],
    [1., 0.01, -0.01, 0.01],
    [1., 0.02, 0., -0.03],
    [1., 0.06, 0., 0.01],
    [1., 0., 0., 0.02],
    [1., -0.02, 0., -0.05],
    [1., 0., 0., 0.],
    [1., 0., 0., -0.]
]


TRACKER_DICT = {
    "upper_base": {
        "smpl": ["CC_Base_Pelvis"],
        "robot": ["base_link"],
        "position_cost": 100.,
        "orientation_cost": 50.,
    },
    "lower_base": {
        "smpl": ["CC_Base_Hip"],
        "robot": ["base_link"],
        "position_cost": 100.,
        "orientation_cost": 50.,
    },
    "leg": {
        "smpl": ["CC_Base_L_KneeShareBone", "CC_Base_L_Foot", "CC_Base_R_KneeShareBone", "CC_Base_R_Foot"],
        "robot": ["leg_l4_link", "leg_l6_link", "leg_r4_link", "leg_r6_link"],
        "position_cost": 100.,
        "orientation_cost": 50.,
    },
    "foot": {
        "smpl": ["CC_Base_L_ToeBaseShareBone", "CC_Base_R_ToeBaseShareBone"],
        "robot": ["leg_l6_link", "leg_r6_link"],
        "position_cost": 200.,
        "orientation_cost": 50.,
    },
    # "arm": {
    #     "smpl": ["CC_Base_L_Upperarm", "CC_Base_L_Forearm", "CC_Base_R_Upperarm", "CC_Base_R_Forearm"],
    #     "robot": ["zarm_l3_link", "zarm_l6_link", "zarm_r3_link", "zarm_r6_link"],
    #     "position_cost": 100.,
    #     "orientation_cost": 0.,
    # },
    # "elbow":{
    #     "smpl": ["CC_Base_L_ElbowShareBone", "CC_Base_R_ElbowShareBone"],
    #     "robot": ["zarm_l4_link", "zarm_r4_link"],
    #     "position_cost": 100.,
    #     "orientation_cost": 0.,
    # },
    # "hand": {
    #     "smpl": ["CC_Base_L_ElbowShareBone", "CC_Base_R_ElbowShareBone"],
    #     "robot": ["zarm_l5_link", "zarm_r5_link"],
    #     "position_cost": 100.,
    #     "orientation_cost": 0.,
    # },
    # "finger": {
    #     "smpl": ["CC_Base_L_Mid1", "CC_Base_R_Mid1"],
    #     "robot": ["zarm_l7_link", "zarm_r7_link"],
    #     "position_cost": 50.,
    #     "orientation_cost": 50.,
    # },
    "head": {
        "smpl": ["CC_Base_NeckTwist01", "CC_Base_Head"],
        "robot": ["zhead_1_link", "zhead_2_link"],
        "position_cost": 200.,
        "orientation_cost": 50.,
    }
}

class BVHPlayer(MotionPlayerBase):
    generator_class = BVH2MJCFGenerator
    def __init__(self, source_file_path, view=True, bvh_type='Reallusion'):
        super().__init__(source_file_path=source_file_path, view=view)
        self.bvh_type = bvh_type
        assert self.bvh_type in ['Reallusion', 'Xingying'], f"Invalid bvh type: {self.bvh_type}"

    def parse_bvh_file(self):
        with open(self.source_file_path, 'r') as f:
            lines = f.readlines()
            for i in range(len(lines)):
                if lines[i].startswith('Frame Time'):
                    frame_time = float(lines[i].split('Frame Time:')[1].strip())
                    frame_rate = 1 / frame_time
                    break
            motion_data = []
            for line in lines[i + 1:]:
                data = [float(x) for x in line.split()]
                if len(data) == 0:
                    break
                motion_data.append(np.array(data).reshape(1, -1))
            motion_data = np.concatenate(motion_data, axis=0)
        return frame_rate, motion_data

    def parse_channel(self, joint_idx, array, channel):
        pos, euler, pos_order, euler_order = [], [], "", ""

        for i, c in enumerate(channel):
            assert c[0] in ['X', 'Y', 'Z'] and c[1:] in ['position', 'rotation']
            if c[1:] == 'position':
                pos.append(array[:, i] / 100)
                pos_order += c[0]
            else:
                euler.append(array[:, i])
                euler_order += c[0]

        if len(pos) == 0:
            pos_array = None
        else:
            pos_array = np.stack(pos, axis=1)
            pos_array = pos_array[:, np.array([pos_order.index('X'), pos_order.index('Y'), pos_order.index('Z')])]
            if self.bvh_type == 'Reallusion' and joint_idx == 0:
                pos_array += self.generator.joint_offsets[0]
                pos_array = Rotation.from_euler('x', 90, degrees=True).apply(pos_array)

        euler_array = np.stack(euler, axis=1)
        r = Rotation.from_euler(euler_order, euler_array, degrees=True)
        if self.bvh_type == 'Reallusion' and joint_idx == 0:
            r = Rotation.from_euler('x', 90, degrees=True) * r

        quat_array = r.as_quat()
        quat_array = np.roll(quat_array, shift=1, axis=1)

        return pos_array, quat_array

    def load_motion_file(self):
        self._frame_rate, self.motion_data = self.parse_bvh_file()

        qpos = []
        begin_idx = 0
        for joint_idx, channel in enumerate(self.generator.channels):
            pos, quat = self.parse_channel(joint_idx, self.motion_data[:, begin_idx:begin_idx + len(channel)], channel)
            begin_idx += len(channel)
            if joint_idx == 0:
                qpos.append(pos)
            qpos.append(quat)

        self._ref_qpos = np.concatenate(qpos, axis=1)

    def load_cali_qpos(self):
        self._cali_qpos = np.zeros(self.mujoco_model.nq)
        self.cali_qpos[3:7] = Rotation.from_euler("xyz", [90, 0, 90], degrees=True).as_quat()[[1, 2, 3, 0]]
        self.cali_qpos[7:] = np.array(CC3PLUS_CALI_QUAT).reshape(-1)
        self.mujoco_data.qpos[:] = self.cali_qpos
        mujoco.mj_forward(self.mujoco_model, self.mujoco_data)

        foot_z = (self.mujoco_data.body("CC_Base_L_ToeBase").xpos[2] + self.mujoco_data.body("CC_Base_R_ToeBase").xpos[2]) / 2.
        self.cali_qpos[2] -= foot_z

    def get_qpos_offset(self, robot_data):
        self.mujoco_data.qpos[:] = self.cali_qpos
        mujoco.mj_forward(self.mujoco_model, self.mujoco_data)

        qpos_list = defaultdict(list)
        for group_name, group_value in TRACKER_DICT.items():
            for smpl_tracker, robot_tracker in zip(group_value["smpl"], group_value["robot"]):
                qpos = np.zeros(7)
                qpos[:3] = self.mujoco_data.body(smpl_tracker).xpos - robot_data.body(robot_tracker).xpos
                qpos[3:] = self.mujoco_data.body(smpl_tracker).xquat
                qpos_list[group_name].append(qpos)

        return qpos_list

def test_qpos_offset():
    from humanoid_retargeting.constant import TRACKER_DICT, ROBOT_DATA_DICT
    from humanoid_retargeting.utils.robot_mjcf import generate_xml
    from humanoid_retargeting import BVH_DATA_PATH
    import time

    robot_name = "kuavo_s45"
    robot_data = ROBOT_DATA_DICT[robot_name]
    bvh_file_path = osp.join(BVH_DATA_PATH, "Reallusion", "newtaichi", '1_Skill.bvh')
    bvh_type = "Reallusion"

    viewer = BVHViewer(source_file_path=bvh_file_path, bvh_type=bvh_type, view=False)
    viewer.load_cali_qpos()



    robot_xml_str = generate_xml(robot_data["body_tree"], robot_data["bodies_data"], robot_name=robot_name)
    robot_model = mujoco.MjModel.from_xml_string(robot_xml_str)
    robot_data = mujoco.MjData(robot_model)

    mujoco.mj_forward(robot_model, robot_data)
    robot_foot_z = robot_data.body("leg_l6_link").xpos[2] - 0.055
    robot_data.joint(robot_model.body("base_link").jntadr[0]).qpos[2] -= robot_foot_z
    mujoco.mj_forward(robot_model, robot_data)

    qpos_list = viewer.get_qpos_offset(robot_data)

    print(qpos_list)

    # scene_str = generate_xml(
    #     robot_data["body_tree"],
    #     robot_data["bodies_data"],
    #     robot_name=robot_name,
    #     add_ground=False,
    #     smpl_root=viewer.generator.xml_root
    # )
    #
    # model = mujoco.MjModel.from_xml_string(scene_str)
    # data = mujoco.MjData(model)
    # data.qpos[:viewer.cali_qpos.shape[0]] = viewer.cali_qpos
    # data.qpos[:viewer.cali_qpos.shape[0]] = viewer.cali_qpos
    # mujoco.mj_forward(model, data)
    #
    # robot_foot_z = data.body("leg_l6_link").xpos[2] - 0.055
    # data.joint(model.body("base_link").jntadr[0]).qpos[2] -= robot_foot_z
    # print(model.body("leg_r2_link").jntadr[0])
    # # data.joint(model.body("zarm_r2_link").jntadr[0]).qpos[0] = -np.pi / 2
    # data.joint("zarm_l2_joint").qpos[0] = np.pi / 2
    # data.joint("zarm_r2_joint").qpos[0] = -np.pi / 2
    # mujoco.mj_forward(model, data)
    #
    # # import pdb
    # # pdb.set_trace()
    #
    # viewer = mujoco.viewer.launch_passive(model, data)
    # viewer.sync()
    # time.sleep(300.)
    # viewer.close()


if __name__ == '__main__':
    from humanoid_retargeting import BVH_DATA_PATH

    # bvh_file_path = osp.join(BVH_DATA_PATH, "Xingying", "LJJ", 'jj02211-jj.bvh')
    # bvh_type = "Xingying"

    # bvh_file_path = osp.join(BVH_DATA_PATH, "Reallusion", "newtaichi", '1_Skill.bvh')
    # bvh_type = "Reallusion"

    # /home/thl/.humanoid_retargeting/bvh_data/01-Pro-SuperPak-2/Above
    bvh_file_path = osp.join(BVH_DATA_PATH, "01-Pro-SuperPak-2", "Above", 'dubstep1 Take 1.bvh')
    bvh_type = "Reallusion"


    player = BVHPlayer(source_file_path=bvh_file_path, bvh_type=bvh_type)
    player.render()
    # viewer.render_cali()
    #
    # test_qpos_offset()