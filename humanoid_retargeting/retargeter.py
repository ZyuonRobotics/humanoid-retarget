import time
import os

import mink
import mujoco
import mujoco.viewer
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from tqdm import tqdm
from hurodes import ROBOTS_PATH
from hurodes.mjcf_generator.generator_composite import MJCFGeneratorComposite

from humanoid_retargeting.motion_player import PLAYERS_CLASS
from humanoid_retargeting.mjcf_generator import generator_class
from humanoid_retargeting.aligner import Aligner
from humanoid_retargeting.mjcf_generator.tracker_generator import TrackerMJCFGenerator

class Retargeter:
    def __init__(
            self,
            source_file_path,
            robot_name,
            generator_type,
            params_name,
            view=True,
            solver="daqp",
            init_frame_loop_num=100,
            mink_solver_dumping=0.1,
            max_velocities = None,
            avoid_ground_collision=False
    ):
        self.source_file_path = source_file_path
        self.robot_name = robot_name
        self.generator_type = generator_type
        self.params_name = params_name
        self.view = view
        self.solver = solver
        self.init_frame_loop_num = init_frame_loop_num
        self.mink_solver_dumping = mink_solver_dumping
        self.max_velocities = max_velocities
        self.avoid_ground_collision = avoid_ground_collision

        self.aligner = Aligner(
            source_file_path=source_file_path,
            robot_name=robot_name,
            generator_type=generator_type,
            params_name=params_name,
            view=False
        )
        self.tracker_offset = self.aligner.get_tracker_offset()
        self.global_body_ratio = self.aligner.get_global_body_ratio()
        self.retarget_params = self.aligner.retarget_params

        self.player = PLAYERS_CLASS[generator_type](
            source_file_path=source_file_path,
            global_body_ratio=self.global_body_ratio * np.array(self.retarget_params.extra_body_ratio),
            relative_body_ratio_dict=self.retarget_params.relative_body_ratio_dict,
        )

        self.human_generator = generator_class[self.generator_type](
            source_file_path=source_file_path,
            global_body_ratio=self.global_body_ratio * np.array(self.retarget_params.extra_body_ratio),
            relative_body_ratio_dict=self.retarget_params.relative_body_ratio_dict,
        )
        self.robot_generator = TrackerMJCFGenerator(
            hrdf_path=os.path.join(ROBOTS_PATH, robot_name),
            tracker_dict=self.retarget_params.tracker_dict,
            tracker_offset=self.tracker_offset
        )
        self.generator = MJCFGeneratorComposite(dict(human=self.human_generator, robot=self.robot_generator))
        self.generator.build()

        # TODO: optimize generator build logics
        self.robot_generator.build()
        self.robot_model = mujoco.MjModel.from_xml_string(self.robot_generator.mjcf_str) # type: ignore
        self.robot_data = mujoco.MjData(self.robot_model) # type: ignore
        self.mink_config = mink.Configuration(self.robot_model)

        self.model = mujoco.MjModel.from_xml_string(self.generator.mjcf_str) # type: ignore
        self.data = mujoco.MjData(self.model) # type: ignore

        self._viewer = None

        self.posture_task: mink.PostureTask | None = None
        self.frame_tasks: list[mink.FrameTask] | None = None
        self.build_mink_tasks()

        self.collision_avoidance_limit = None
        self.configuration_limit = None
        self.velocity_limit = None
        self.build_mink_limits()

        self.robot_ref_qpos = np.zeros([self.frame_num, self.robot_model.nq])
        self.robot_ref_qvel = np.zeros([self.frame_num, self.robot_model.nv])

    @property
    def viewer(self):
        assert self.view, "Viewer is not enabled"
        if self._viewer is None:
            self._viewer = mujoco.viewer.launch_passive(self.model, self.data)
        return self._viewer

    @property
    def all_tasks(self):
        assert self.posture_task is not None and self.frame_tasks is not None
        return [self.posture_task] + self.frame_tasks

    @property
    def all_limits(self):
        limits = [self.configuration_limit, self.velocity_limit, self.collision_avoidance_limit]
        return list(filter(lambda l: l is not None, limits))

    @property
    def human_trackers(self):
        return [s for group_value in self.retarget_params.tracker_dict.values() for s in group_value.human]

    @property
    def frame_num(self):
        return self.player.frame_num

    @property
    def frame_rate(self):
        return self.player.frame_rate

    def build_mink_limits(self):
        self.configuration_limit = mink.ConfigurationLimit(model=self.robot_model)
        if self.avoid_ground_collision:
            self.collision_avoidance_limit = mink.CollisionAvoidanceLimit(
                model=self.robot_model,
                geom_pairs=[(["floor"], self.robot_generator.all_collision_names)]
            )
        if self.max_velocities is not None:
            if isinstance(self.max_velocities, (int, float)):
                max_velocities = np.full(self.model.nv - 7, self.max_velocities, dtype=np.float32)
            elif isinstance(self.max_velocities, (list, np.ndarray)):
                assert len(self.max_velocities) == self.model.nv - 7
                max_velocities = np.array(self.max_velocities)
            else:
                raise NotImplemented
            joint_names = [self.model.joint(i).name for i in range(7, self.model.njnt)]
            velocities_dict = {name: vel for name, vel in zip(joint_names, max_velocities)}
            self.velocity_limit = mink.VelocityLimit(self.model, velocities_dict)

    def build_mink_tasks(self):
        self.posture_task = mink.PostureTask(self.robot_model, cost=200.0)
        self.frame_tasks = []
        for group_name, group_value in self.retarget_params.tracker_dict.items():
            for human_body_name, robot_body_name in zip(group_value.human, group_value.robot):
                task = mink.FrameTask(
                    frame_name=f"{robot_body_name}_{human_body_name}_tracker",
                    frame_type="site",
                    position_cost=group_value.position_cost,
                    orientation_cost=group_value.orientation_cost,
                    lm_damping=1.)
                self.frame_tasks.append(task)


    def run_ik(self):
        assert self.posture_task is not None and self.frame_tasks is not None
        
        for frame_idx in tqdm(range(self.frame_num), disable=self.player is None):
            self.player.sync_data(frame_idx)

            self.posture_task.set_target_from_configuration(self.mink_config)
            for j in range(len(self.frame_tasks)):
                self.frame_tasks[j].set_target(mink.SE3.from_rotation_and_translation(
                    mink.SO3.from_matrix(self.player.data.body(self.human_trackers[j]).xmat.reshape([3, 3])),
                    self.player.data.body(self.human_trackers[j]).xpos
                ))

            for _ in range(self.init_frame_loop_num if frame_idx == 0 else 1):
                vel = mink.solve_ik(
                    configuration=self.mink_config,
                    tasks=self.all_tasks,
                    limits=self.all_limits,
                    dt=1. / self.frame_rate,
                    solver=self.solver,
                    damping=self.mink_solver_dumping
                )
                self.mink_config.integrate_inplace(vel, 1. / self.frame_rate)

            self.robot_ref_qvel[frame_idx, :] = vel.copy()
            self.robot_ref_qpos[frame_idx, :] = self.mink_config.q.copy()

            self.data.qpos[:self.player.model.nq] = self.player.ref_qpos[frame_idx, :]
            self.data.qpos[self.player.model.nq:] = self.robot_ref_qpos[frame_idx, :]
            self.data.qvel[self.player.model.nv:] = self.robot_ref_qvel[frame_idx, :]
            mujoco.mj_forward(self.model, self.data) # type: ignore

            if self.view:
                self.viewer.sync()

    def view_frame(self, frame_id=0, offset=None):
        offset = np.array(offset) if offset is not None else np.zeros(3)
        self.data.qpos[:self.player.model.nq] = self.player.ref_qpos[frame_id, :]
        self.data.qpos[-self.robot_model.nq:] = self.robot_ref_qpos[frame_id, :]
        self.data.qpos[-self.robot_model.nq:-self.robot_model.nq + 2] += offset[:2]
        mujoco.mj_forward(self.model, self.data) # type: ignore
        self.viewer.sync()


    def interpolate(self, target_framerate=100):
        t_original = np.linspace(0, (self.frame_num - 1) / self.frame_rate, self.frame_num)
        new_frame_num = int(self.frame_num * target_framerate / self.frame_rate)
        t_new = np.linspace(0, (self.frame_num - 1) / self.frame_rate, new_frame_num)

        res_qpos = interp1d(t_original, self.robot_ref_qpos, axis=0)(t_new)
        res_qvel = interp1d(t_original, self.robot_ref_qvel, axis=0)(t_new)
        return res_qpos, res_qvel, new_frame_num


    def save_as_npz(self, res_path, target_framerate=100):
        res_qpos, res_qvel, frame_num = self.interpolate(target_framerate=target_framerate)

        np.savez_compressed(
            res_path,
            root_trans=res_qpos[:, :3],
            root_quat=res_qpos[:, [4, 5, 6, 3]],  # from w,x,y,z to x,y,z,w
            joint_pos=res_qpos[:, 7:],
            root_lin_vel=res_qvel[:, :3],
            root_ang_vel=res_qvel[:, 3:6],
            joint_vel=res_qvel[:, 6:],
            frame_rate=target_framerate,
            frame=frame_num
        )


    def save_as_csv(self, res_path, target_framerate=100):
        res_qpos, res_qvel, frame_num = self.interpolate(target_framerate=target_framerate)
        res = np.concatenate([res_qpos, res_qvel], axis=1)
        pd.DataFrame(res).to_csv(res_path, header=False, index=False)


    def play(self, speed=1., loop=True, offset=None):
        assert self.viewer is not None, "Viewer is not initialized"
        while True:
            for frame_id in range(self.frame_num):
                step_start = time.time()
                self.view_frame(frame_id, offset)
                time_until_next_step = 1 / self.frame_rate / speed - (time.time() - step_start)
                if not self.viewer.is_running():
                    break
                if time_until_next_step > 0:
                    time.sleep(time_until_next_step)
            if not loop:
                break
            if not self.viewer.is_running():
                break


    def close(self):
        if self.view:
            assert self.viewer is not None
            self.viewer.close()
