import os.path as osp
import xml.etree.ElementTree as ET

import numpy as np

from humanoid_retargeting import PROJECT_PATH, SMPLH_PATH, DMPLS_PATH
from humanoid_retargeting.mjcf_generator.constants import *
from humanoid_retargeting.mjcf_generator.generator_base import RetargetingMJCFGenerator


def array2str(array):
    return " ".join(map(lambda x: str(round(x, 4)), array))


class SMPL2MJCFGenerator(RetargetingMJCFGenerator):
    def __init__(self, source_file_path, using_dmpl=False):
        super().__init__(source_file_path=source_file_path)

        self.using_dmpl = using_dmpl

        self.vertices = None
        self.kintree_table = None
        self.bones = None
        self.weights = None
        self.faces = None

    @staticmethod
    def create_body_element(name, pos, joint_type="ball", geom=True):
        body = ET.Element('body', name=name, pos=pos)
        if joint_type:
            ET.SubElement(body, 'joint', type=joint_type)
        if geom:
            ET.SubElement(body, 'geom', size="0.01", contype="0", conaffinity="0")
        return body

    def build_skeleton(self, parent, joint_names, relative_jacob, kintree_table, index=0):
        if index >= len(joint_names):
            return
        joint_name = joint_names[index]
        pos = array2str(relative_jacob[index])
        body = self.create_body_element(joint_name, pos, joint_type="free" if index == 0 else "ball")
        parent.append(body)

        for child_idx in np.where(kintree_table[0] == index)[0]:
            self.build_skeleton(body, joint_names, relative_jacob, kintree_table, child_idx)

    def generate(self):
        relative_jacob = self.bones.copy()
        relative_jacob[1:] -= self.bones[self.kintree_table[0, 1:]]

        worldbody = ET.SubElement(self.xml_root, 'worldbody')
        self.build_skeleton(worldbody, SMPLH_JOINT_NAMES, relative_jacob, self.kintree_table)

        deformable = ET.SubElement(self.xml_root, 'deformable')
        skin = ET.SubElement(  deformable,  'skin', attrib=dict(
            rgba="1 1 1 0.5",
            vertex=array2str(self.vertices.reshape([-1, ])),
            face=array2str(self.faces.reshape([-1, ]))
        ))
        for joint_id in range(self.bones.shape[0]):
            full_weight = self.weights[:, joint_id]
            vertex_ids = np.nonzero(full_weight)[0]
            vertex_weight = full_weight[vertex_ids]
            ET.SubElement(skin, 'bone', attrib=dict(
                body=SMPLH_JOINT_NAMES[joint_id],
                bindpos=array2str(self.bones[joint_id]),
                bindquat="1 0 0 0",
                vertid=array2str(vertex_ids),
                vertweight=array2str(vertex_weight)
            ))

    def load(self):
        bdata = np.load(self.source_file_path)
        gender = str(bdata['gender'].astype(str))

        with np.load(osp.join(SMPLH_PATH, gender, "model.npz"), allow_pickle=True) as data:
            smpl_dict = {key: data[key] for key in data.files}

        vertices = smpl_dict["v_template"] + (smpl_dict["shapedirs"] @ bdata["betas"]).reshape([-1, 3])
        vertices[:, :] = vertices[:, [2, 0, 1]]

        self.vertices = vertices
        self.kintree_table = smpl_dict["kintree_table"]
        self.bones = smpl_dict["J_regressor"] @ vertices
        self.weights = smpl_dict["weights"]
        self.faces = smpl_dict["f"]


if __name__ == '__main__':
    import mujoco
    import mujoco.viewer

    from humanoid_retargeting import AMASS_DATA_PATH

    amass_file_path = osp.join(AMASS_DATA_PATH, "amass", 'CMU', "12", "4_tai_chi_stageii.npz")

    generator = SMPL2MJCFGenerator(amass_file_path)
    generator.load()
    generator.generate()
    generator.add_scene()
    mjcf_str = generator.mjcf_str

    m = mujoco.MjModel.from_xml_string(mjcf_str)
    d = mujoco.MjData(m)
    d.qpos[2] = 1
    with mujoco.viewer.launch_passive(m, d) as viewer:
        while viewer.is_running():
            mujoco.mj_step(m, d)
            viewer.sync()
