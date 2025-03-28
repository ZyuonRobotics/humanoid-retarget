from os import path as osp
from collections import defaultdict
import time

import mujoco.msh2obj
import mujoco
import mujoco.viewer
import numpy as np
from scipy.spatial.transform import Rotation

from humanoid_retargeting import PROJECT_PATH, XML_PATH_DICT, AMASS_DATA_PATH
from humanoid_retargeting.constant import TRACKER_DICT, ROBOT_DATA_DICT
from humanoid_retargeting.utils.robot_mjcf import generate_xml
from humanoid_retargeting.utils.rot import euler2quat


def get_qpos_list(amass_npz_fname, robot_name="kuavo_s40"):
    robot_data_dict = ROBOT_DATA_DICT[robot_name]
    
    mjcf_str, xml_root, scale = amass2mjcf(amass_npz_fname, height=robot_data_dict["height"])

    smpl_model = mujoco.MjModel.from_xml_string(mjcf_str)
    smpl_data = mujoco.MjData(smpl_model)
    smpl_data.joint(smpl_model.body("left_shoulder").jntadr[0]).ref_qpos[0:4] = euler2quat(-80, -5, 0)
    smpl_data.joint(smpl_model.body("right_shoulder").jntadr[0]).ref_qpos[0:4] = euler2quat(80, -5, 0)
    # smpl_data.joint(smpl_model.body("left_hip").jntadr[0]).qpos[0:4] = euler2quat(-1, 0, 0)
    # smpl_data.joint(smpl_model.body("right_hip").jntadr[0]).qpos[0:4] = euler2quat(1, 0, 0)
    mujoco.mj_forward(smpl_model, smpl_data)
    smpl_foot_z = (smpl_data.body("left_ankle").xpos[2] + smpl_data.body("right_ankle").xpos[2])/2.

    robot_xml_str = generate_xml(robot_data_dict["body_tree"], robot_data_dict["bodies_data"], robot_name=robot_name)
    kuavo_model = mujoco.MjModel.from_xml_string(robot_xml_str)
    kuavo_data = mujoco.MjData(kuavo_model)
    mujoco.mj_forward(kuavo_model, kuavo_data)
    kuavo_foot_z = kuavo_data.body("leg_l6_link").xpos[2]
    kuavo_data.qpos[2] += smpl_foot_z - kuavo_foot_z
    mujoco.mj_forward(kuavo_model, kuavo_data)

    qpos_list = defaultdict(list)
    for group_name, group_value in TRACKER_DICT.items():
        for smpl_tracker, robot_tracker in zip(group_value["smpl"], group_value["robot"]):
            qpos = np.zeros(7)
            qpos[:3] = smpl_data.body(smpl_tracker).xpos - kuavo_data.body(robot_tracker).xpos
            qpos[3:] = smpl_data.body(smpl_tracker).xquat
            qpos_list[group_name].append(qpos)
    return qpos_list


if __name__ == '__main__':
    robot_name = "kuavo_s45"
    robot_data = ROBOT_DATA_DICT[robot_name]

    amass_npz_fname = osp.join(AMASS_DATA_PATH, "amass", 'CMU', "12", "4_tai_chi_stageii.npz")
    tracker_offset_dict = get_qpos_list(amass_npz_fname, robot_name=robot_name)
    smpl_mjcf_str, smpl_xml_root, scale = amass2mjcf(amass_npz_fname, height=robot_data["height"])
    scene_str = generate_xml(robot_data["body_tree"], robot_data["bodies_data"], robot_name=robot_name,
                             add_ground=False, smpl_root=smpl_xml_root)

    model = mujoco.MjModel.from_xml_string(scene_str)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)

    # data.joint("zarm_l2_joint").qpos[0] = 1.57
    # data.joint("zarm_r2_joint").qpos[0] = -1.57
    data.joint(model.body("left_shoulder").jntadr[0]).ref_qpos[0:4] = euler2quat(-80, -5, 0)
    data.joint(model.body("right_shoulder").jntadr[0]).ref_qpos[0:4] = euler2quat(80, -5, 0)
    # data.joint(model.body("left_wrist").jntadr[0]).qpos[0:4] = euler2quat(0, 0, 5)
    # data.joint(model.body("right_elbow").jntadr[0]).qpos[0:4] = euler2quat(0, 0, 5)
    # data.joint(model.body("left_hip").jntadr[0]).qpos[0:4] = euler2quat(-1, 0, 0)
    # data.joint(model.body("right_hip").jntadr[0]).qpos[0:4] = euler2quat(1, 0, 0)

    smpl_foot_z = (data.body("left_ankle").xpos[2] + data.body("right_ankle").xpos[2])/2.
    robot_foot_z = data.body("leg_l6_link").xpos[2]
    data.joint(model.body("base_link").jntadr[0]).ref_qpos[2] += smpl_foot_z - robot_foot_z
    
    viewer = mujoco.viewer.launch_passive(model, data)
    viewer.sync()
    time.sleep(300.)
    viewer.close()











