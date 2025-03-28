from os import path as osp
import glob
import time
import numpy as np
import matplotlib.pyplot as plt
import mujoco
import mujoco.viewer

from amass2mjcf import amass2mjcf

SMPLH_JOINT_NAMES = [
    'pelvis',
    'left_hip',
    'right_hip',
    'spine1',
    'left_knee',
    'right_knee',
    'spine2',
    'left_ankle',
    'right_ankle',
    'spine3',
    'left_foot',
    'right_foot',
    'neck',
    'left_collar',
    'right_collar',
    'head',
    'left_shoulder',
    'right_shoulder',
    'left_elbow',
    'right_elbow',
    'left_wrist',
    'right_wrist',
    'left_index1',
    'left_index2',
    'left_index3',
    'left_middle1',
    'left_middle2',
    'left_middle3',
    'left_pinky1',
    'left_pinky2',
    'left_pinky3',
    'left_ring1',
    'left_ring2',
    'left_ring3',
    'left_thumb1',
    'left_thumb2',
    'left_thumb3',
    'right_index1',
    'right_index2',
    'right_index3',
    'right_middle1',
    'right_middle2',
    'right_middle3',
    'right_pinky1',
    'right_pinky2',
    'right_pinky3',
    'right_ring1',
    'right_ring2',
    'right_ring3',
    'right_thumb1',
    'right_thumb2',
    'right_thumb3',
]

scene_str = '''
<mujoco model="smpl scene">
  <compiler angle="radian" autolimits='true' />
  <include file="smpl.xml"/>
  <include file="robot-assets/kuavo_s40/mjcf/biped_s40.xml"/>

  <visual>
    <headlight diffuse="0.6 0.6 0.6" ambient="0.3 0.3 0.3" specular="0 0 0"/>
    <rgba haze="0.15 0.25 0.35 1"/>
    <global azimuth="160" elevation="-20"/>
  </visual>

  <asset>
    <texture type="skybox" builtin="gradient" rgb1="0.3 0.5 0.7" rgb2="0 0 0" width="512" height="3072"/>
    <texture type="2d" name="groundplane" builtin="checker" mark="edge" rgb1="0.2 0.3 0.4" rgb2="0.1 0.2 0.3"
      markrgb="0.8 0.8 0.8" width="300" height="300"/>
    <material name="groundplane" texture="groundplane" texuniform="true" texrepeat="5 5" reflectance="0.2"/>
  </asset>

  <worldbody>
    <light pos="0 0 3.5" dir="0 0 -1" directional="true"/>
    <geom name="floor" size="0 0 0.05" type="plane" material="groundplane" condim='3' conaffinity='15'/>

  </worldbody>
</mujoco>
'''

class AmassRetargetVanilla(object):

    def __init__(self, amass_npz_fname, skin_inline=True, axis_z_up=True, height=None):
        _, scale = amass2mjcf(amass_npz_fname,
                             "smpl.xml",
                             skin_inline=skin_inline,
                             axis_z_up=axis_z_up,
                             height=height)
        self.model = mujoco.MjModel.from_xml_string(scene_str)
        self.data = mujoco.MjData(self.model)

        # mujoco.mj_forward(self.model, self.data)
        # print(f'robot height:{self.data.body("leg_l5_link").xpos[2] - self.data.body("zarm_l2_link").xpos[2]}')

        self.viewer = mujoco.viewer.launch_passive(self.model, self.data)
        self.viewer.sync()

        bdata = np.load(amass_npz_fname)
        self.framerate = 120
        try:
            self.framerate = bdata['mocap_framerate']
        except:
            print("AmassViewer.__init__() Warning: framerate not found from file.")
        self.framerate *= np.sqrt(scale)
        self.root_orient = bdata['poses'][:, :3]
        self.pose_body = bdata['poses'][:, 3:66]
        self.pose_hand = bdata['poses'][:, 66:]
        self.so3_all = np.hstack([self.root_orient, self.pose_body, self.pose_hand]).reshape([-1, 52, 3])
        self.trans = bdata['trans'] * scale + self.model.body("pelvis").pos[[1,2,0] if axis_z_up else [0,1,2]]
        if axis_z_up:
            self.so3_all[:,1:,:] = self.so3_all[:, 1:, [2,0,1]]

        self.nframes = len(self.trans)
        self.qposs = np.zeros([self.nframes, self.data.qpos.shape[0]])
        self.qposs[:, 0:3] = self.trans
        def so3_to_quat(batched_so3, verbose=False): # quat: [w, x, y, z]
            quat = np.zeros([batched_so3.shape[0], 4])
            angle = np.linalg.norm(batched_so3, axis=1, keepdims=True)
            quat[:, 1:4] = np.where(angle>1e-6, batched_so3 / angle * np.sin(angle/2), 0.)
            quat[:, 0] = np.cos(angle/2)[:,0]
            return quat
        
        if axis_z_up:
            mat = 0.5*np.array([[1,-1,-1,-1], [1,1,1,-1], [1,-1,1,1], [1,1,-1,1]])
            self.qposs[:, 3:7] = so3_to_quat(self.so3_all[:, 0]) @ mat
        else:
            self.qposs[:, 3:7] = so3_to_quat(self.so3_all[:, 0])
        for joint_id in range(1, 52):
            joint_qposadr = self.model.joint(self.model.body(SMPLH_JOINT_NAMES[joint_id]).jntadr[0]).qposadr[0]
            self.qposs[:, joint_qposadr:joint_qposadr+4] = so3_to_quat(self.so3_all[:, joint_id])
        if axis_z_up:
            joint_qposadr = self.model.joint(self.model.body("base_link").jntadr[0]).qposadr[0]
            self.qposs[:, joint_qposadr:joint_qposadr+7] = self.qposs[:, 0:7]
            joint_qposadr = self.model.joint("leg_l1_joint").qposadr[0]
            self.qposs[:, joint_qposadr] = self.so3_all[:, SMPLH_JOINT_NAMES.index("left_hip"), 0]
            joint_qposadr = self.model.joint("leg_l2_joint").qposadr[0]
            self.qposs[:, joint_qposadr] = self.so3_all[:, SMPLH_JOINT_NAMES.index("left_hip"), 2]
            joint_qposadr = self.model.joint("leg_l3_joint").qposadr[0]
            self.qposs[:, joint_qposadr] = self.so3_all[:, SMPLH_JOINT_NAMES.index("left_hip"), 1]
            joint_qposadr = self.model.joint("leg_l4_joint").qposadr[0]
            self.qposs[:, joint_qposadr] = self.so3_all[:, SMPLH_JOINT_NAMES.index("left_knee"), 1]
            joint_qposadr = self.model.joint("leg_l5_joint").qposadr[0]
            self.qposs[:, joint_qposadr] = self.so3_all[:, SMPLH_JOINT_NAMES.index("left_ankle"), 1]
            joint_qposadr = self.model.joint("leg_l6_joint").qposadr[0]
            self.qposs[:, joint_qposadr] = self.so3_all[:, SMPLH_JOINT_NAMES.index("left_ankle"), 0]
            self.qposs[:, joint_qposadr:joint_qposadr+7] = self.qposs[:, 0:7]
            joint_qposadr = self.model.joint("leg_r1_joint").qposadr[0]
            self.qposs[:, joint_qposadr] = self.so3_all[:, SMPLH_JOINT_NAMES.index("right_hip"), 0]
            joint_qposadr = self.model.joint("leg_r2_joint").qposadr[0]
            self.qposs[:, joint_qposadr] = self.so3_all[:, SMPLH_JOINT_NAMES.index("right_hip"), 2]
            joint_qposadr = self.model.joint("leg_r3_joint").qposadr[0]
            self.qposs[:, joint_qposadr] = self.so3_all[:, SMPLH_JOINT_NAMES.index("right_hip"), 1]
            joint_qposadr = self.model.joint("leg_r4_joint").qposadr[0]
            self.qposs[:, joint_qposadr] = self.so3_all[:, SMPLH_JOINT_NAMES.index("right_knee"), 1]
            joint_qposadr = self.model.joint("leg_r5_joint").qposadr[0]
            self.qposs[:, joint_qposadr] = self.so3_all[:, SMPLH_JOINT_NAMES.index("right_ankle"), 1]
            joint_qposadr = self.model.joint("leg_r6_joint").qposadr[0]
            self.qposs[:, joint_qposadr] = self.so3_all[:, SMPLH_JOINT_NAMES.index("right_ankle"), 0]
            joint_qposadr = self.model.joint("zarm_l1_joint").qposadr[0]
            self.qposs[:, joint_qposadr] = (self.so3_all[:, SMPLH_JOINT_NAMES.index("left_collar"), 2]
                                            +self.so3_all[:, SMPLH_JOINT_NAMES.index("left_shoulder"), 2])
            joint_qposadr = self.model.joint("zarm_l2_joint").qposadr[0]
            self.qposs[:, joint_qposadr] = (self.so3_all[:, SMPLH_JOINT_NAMES.index("left_collar"), 0]
                                            +self.so3_all[:, SMPLH_JOINT_NAMES.index("left_shoulder"), 0]) + np.pi/2
            joint_qposadr = self.model.joint("zarm_l4_joint").qposadr[0]
            self.qposs[:, joint_qposadr] = self.so3_all[:, SMPLH_JOINT_NAMES.index("left_elbow"), 2]
            joint_qposadr = self.model.joint("zarm_r1_joint").qposadr[0]
            self.qposs[:, joint_qposadr] = (self.so3_all[:, SMPLH_JOINT_NAMES.index("right_collar"), 2]
                                            +self.so3_all[:, SMPLH_JOINT_NAMES.index("right_shoulder"), 2])
            joint_qposadr = self.model.joint("zarm_r2_joint").qposadr[0]
            self.qposs[:, joint_qposadr] = (self.so3_all[:, SMPLH_JOINT_NAMES.index("right_collar"), 0]
                                            +self.so3_all[:, SMPLH_JOINT_NAMES.index("right_shoulder"), 0]) - np.pi/2
            joint_qposadr = self.model.joint("zarm_r4_joint").qposadr[0]
            self.qposs[:, joint_qposadr] = -self.so3_all[:, SMPLH_JOINT_NAMES.index("right_elbow"), 2]
    
    def view_frame(self, frame_id=0):
        self.data.qpos[:] = self.qposs[frame_id, :]
        # self.data.qpos[3:7] = res
        mujoco.mj_forward(self.model, self.data)
        self.viewer.sync()
    
    def play(self, speed=1., loop=True):
        while(True):
            for frame_id in range(self.nframes):
                step_start = time.time()
                self.view_frame(frame_id)
                time_until_next_step = 1/self.framerate/speed - (time.time() - step_start)
                if not self.viewer.is_running():
                    break
                if time_until_next_step > 0:
                    time.sleep(time_until_next_step)
            if(not loop):
                break
            if not self.viewer.is_running():
                break
    
    def close(self):
        self.viewer.close()



if __name__ == "__main__":
    support_dir = './support_data/'
    # amass_npz_fname = osp.join(support_dir, 'github_data/amass_sample.npz')
    # amass_npz_fname = osp.join(support_dir, 'github_data/dmpl_sample.npz')
    amass_npz_fname = osp.join(support_dir, 'github_data/ACCAD/Female1Walking_c3d/B1 - stand to walk_poses.npz')
    # amass_npz_fname = osp.join(support_dir, 'github_data/ACCAD/Female1General_c3d/A6 - lift box_poses.npz')
    # for data_path in glob.glob('support_data/github_data/ACCAD/**/*.npz', recursive=True):
    #     print(f"playing {data_path}")
    #     amass_npz_fname = data_path
    av = AmassRetargetVanilla(amass_npz_fname, skin_inline=True, axis_z_up=True, height=1.11)
    av.play(speed=1.,
            # loop=False,
            # loop=True
            )
    av.close()
        









