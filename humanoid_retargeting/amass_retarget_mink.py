from os import path as osp
import os
import time

import numpy as np
import mujoco
import mujoco.viewer
import mink
from tqdm import tqdm
from scipy.interpolate import interp1d
import pandas as pd

from humanoid_retargeting import PROJECT_PATH, AMASS_DATA_PATH, BVH_DATA_PATH
from humanoid_retargeting.constant import TRACKER_DICT, ROBOT_DATA_DICT
from humanoid_retargeting.motion_viewer.bvh_viewer import BVHViewer
from humanoid_retargeting.align_robot_w_amass import get_qpos_list
from humanoid_retargeting.utils.robot_mjcf import generate_xml



def get_qpos_list(amass_npz_fname, robot_name="kuavo_s45"):
    from humanoid_retargeting.constant import TRACKER_DICT, ROBOT_DATA_DICT
    from humanoid_retargeting.utils.robot_mjcf import generate_xml
    from humanoid_retargeting import BVH_DATA_PATH

    robot_data = ROBOT_DATA_DICT[robot_name]
    bvh_type = "Reallusion"

    viewer = BVHViewer(source_file_path=amass_npz_fname, bvh_type=bvh_type, view=False)
    viewer.load_cali_qpos()

    robot_xml_str = generate_xml(robot_data["body_tree"], robot_data["bodies_data"], robot_name=robot_name)
    robot_model = mujoco.MjModel.from_xml_string(robot_xml_str)
    robot_data = mujoco.MjData(robot_model)

    mujoco.mj_forward(robot_model, robot_data)
    robot_foot_z = robot_data.body("leg_l6_link").xpos[2] - 0.055
    robot_data.joint(robot_model.body("base_link").jntadr[0]).qpos[2] -= robot_foot_z
    mujoco.mj_forward(robot_model, robot_data)

    qpos_list = viewer.get_qpos_offset(robot_data)

    return qpos_list

class AmassRetargetMink(object):

    def __init__(self, amass_npz_fname, robot_name="kuavo_s40", view=True):
        self.robot_name = robot_name
        self.robot_data = ROBOT_DATA_DICT[robot_name]
        self.view = view

        self.viewer = BVHViewer(amass_npz_fname, view=False)
        tracker_qpos_list = get_qpos_list(amass_npz_fname, robot_name=robot_name)

        kuavo_str = generate_xml(
            body_tree=self.robot_data["body_tree"],
            bodies_data=self.robot_data["bodies_data"],
            robot_name=robot_name,
            tracker_qpos_list=tracker_qpos_list,
        )
        self.kuavo_model = mujoco.MjModel.from_xml_string(kuavo_str)
        self.kuavo_data = mujoco.MjData(self.kuavo_model)
        self.config = mink.Configuration(self.kuavo_model)

        scene_str = generate_xml(
            body_tree=self.robot_data["body_tree"],
            bodies_data=self.robot_data["bodies_data"],
            robot_name=robot_name,
            tracker_qpos_list=tracker_qpos_list,
            smpl_root=self.viewer.generator.xml_root
        )
        self.model = mujoco.MjModel.from_xml_string(scene_str)
        self.data = mujoco.MjData(self.model)
        if self.view:
            self.viewer = mujoco.viewer.launch_passive(self.model, self.data)
            self.viewer.sync()
        else:
            self.viewer = None

        self.posture_task = mink.PostureTask(self.kuavo_model, cost=200.0)
        self.frame_tasks = []
        for group_name, group_value in TRACKER_DICT.items():
            for smpl_tracker, robot_tracker in zip(group_value["smpl"], group_value["robot"]):
                task = mink.FrameTask(
                    frame_name=f"{robot_tracker}_{smpl_tracker}_track",
                    frame_type="site",
                    position_cost=group_value["position_cost"],
                    orientation_cost=group_value["orientation_cost"],
                    lm_damping=1.)
                self.frame_tasks.append(task)
        self.all_tasks = [self.posture_task] + self.frame_tasks
        self.frame_task_num = len(self.frame_tasks)
        self.smpl_site_names = [s for group_value in TRACKER_DICT.values() for s in group_value["smpl"]]

        self.nframes = self.viewer.nframes
        self.framerate = self.viewer.framerate
        self.robot_ref_qpos = np.zeros([self.nframes, self.kuavo_model.nq])
        self.robot_ref_qvel = np.zeros([self.nframes, self.kuavo_model.nv])

        self.lowest_foot_z = self.robot_data["foot_thickness"]

    def run_ik(self):
        for i in tqdm(range(self.nframes), disable=self.viewer is None):
            self.viewer.data.ref_qpos[:] = self.viewer.ref_qpos[i, :]
            mujoco.mj_forward(self.viewer.model, self.viewer.data)
            self.posture_task.set_target_from_configuration(self.config)
            for j in range(self.frame_task_num):
                self.frame_tasks[j].set_target(mink.SE3.from_rotation_and_translation(
                    mink.SO3.from_matrix(self.viewer.data.body(self.smpl_site_names[j]).xmat.reshape([3, 3])),
                    self.viewer.data.body(self.smpl_site_names[j]).xpos
                ))

            for _ in range(100 if i == 0 else 1):
                vel = mink.solve_ik(self.config, self.all_tasks, 1. / self.framerate, "quadprog", 1e-1)
                self.config.integrate_inplace(vel, 1. / self.framerate)

            self.robot_ref_qvel[i, :] = vel.copy()
            self.robot_ref_qpos[i, :] = self.config.q.copy()

            self.data.qpos[:self.viewer.model.nq] = self.viewer.ref_qpos[i, :]
            self.data.qpos[self.viewer.model.nq:] = self.robot_ref_qpos[i, :]
            self.data.qvel[self.viewer.model.nv:] = self.robot_ref_qvel[i, :]
            mujoco.mj_forward(self.model, self.data)

            if self.view:
                self.viewer.sync()
        self.viewer.ref_qpos[:, 2] += (self.robot_data["foot_thickness"] - self.lowest_foot_z)
        self.robot_ref_qpos[:, 2] += (self.robot_data["foot_thickness"] - self.lowest_foot_z)

    def view_frame(self, frame_id=0, offset=None):
        vec = offset if offset is not None else np.zeros(3)
        res = np.zeros(3)
        quat = self.viewer.ref_qpos[0, 3:7]
        mujoco.mju_rotVecQuat(res, vec, quat)
        self.data.qpos[:self.viewer.model.nq] = self.viewer.ref_qpos[frame_id, :]
        self.data.qpos[-self.kuavo_model.nq:] = self.robot_ref_qpos[frame_id, :]
        self.data.qpos[-self.kuavo_model.nq:-self.kuavo_model.nq + 2] += res[:2]
        mujoco.mj_forward(self.model, self.data)
        self.viewer.sync()

    def interpolate(self, target_framerate=100):
        t_original = np.linspace(0, (self.nframes - 1) / self.framerate, self.nframes)
        new_nframes = int(self.nframes * target_framerate / self.framerate)
        t_new = np.linspace(0, (self.nframes  - 1) / self.framerate, new_nframes)

        res_qpos = interp1d(t_original, self.robot_ref_qpos, axis=0)(t_new)
        res_qvel = interp1d(t_original, self.robot_ref_qvel, axis=0)(t_new)
        return res_qpos, res_qvel, new_nframes

    def save_as_npy(self, res_path, target_framerate=100):
        res_qpos, res_qvel, nframes = self.interpolate(target_framerate=target_framerate)

        res_dict = {
            "root_trans": res_qpos[:, :3],
            "root_quat": res_qpos[:, [4, 5, 6, 3]], # from w,x,y,z to x,y,z,w
            "joint_pos": res_qpos[:, 7:],
            "root_lin_vel": res_qvel[:, :3],
            "root_ang_vel": res_qvel[:, 3:6],
            "joint_vel": res_qvel[:, 6:],
            "frame_rate": target_framerate,
            "frames": nframes
        }
        np.save(res_path, res_dict)

    def save_as_csv(self, res_path, target_framerate=100):
        res_qpos, res_qvel, nframes = self.interpolate(target_framerate=target_framerate)
        res = np.concatenate([res_qpos, res_qvel], axis=1)
        pd.DataFrame(res).to_csv(res_path, header=None, index=None)

    def play(self, speed=1., loop=True, offset=None):
        assert self.viewer is not None, "Viewer is not initialized"
        while True:
            for frame_id in range(self.nframes):
                step_start = time.time()
                self.view_frame(frame_id, offset)
                time_until_next_step = 1 / self.framerate / speed - (time.time() - step_start)
                if not self.viewer.is_running():
                    break
                if time_until_next_step > 0:
                    time.sleep(time_until_next_step)
            if not loop:
                break
            if not self.viewer.is_running():
                break

    def close(self):
        if self.viewer is not None:
            self.viewer.close()


if __name__ == '__main__':
    robot_name = "kuavo_s45"
    bvh_file_path = osp.join(BVH_DATA_PATH, "Reallusion", "newtaichi", '1_Skill.bvh')
    bvh_type = "Reallusion"

    ar = AmassRetargetMink(bvh_file_path, robot_name=robot_name, view=True)
    ar.run_ik()
    ar.save_as_npy("taichi.npy", target_framerate=100)
    ar.save_as_csv("taichi.csv", target_framerate=100)

    ar.play(speed=1., offset=np.array([0., 1., 0.]))
    ar.close()
