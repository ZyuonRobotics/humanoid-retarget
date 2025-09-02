import os.path as osp
import xml.etree.ElementTree as ET
import pickle

import numpy as np

from humanoid_retargeting import SMPL_PATH, SMPLH_PATH
from humanoid_retargeting.mjcf_generator.constants import *
from humanoid_retargeting.mjcf_generator.retargeting_generator_base import (
    RetargetingMJCFGeneratorBase, get_prefix_name, array_to_string
)


class SMPL2MJCFGenerator(RetargetingMJCFGeneratorBase):
    generator_type = "smpl"

    def __init__(
        self, 
        source_file_path=None,
        global_body_ratio=1.0, 
        relative_body_ratio_dict=None,
        using_dmpl=False,
        geom_size=0.01,
        generate_skin=False,
        **kwargs
    ):
        super().__init__(
            global_body_ratio=global_body_ratio,
            relative_body_ratio_dict=relative_body_ratio_dict,
            geom_size=geom_size,
            **kwargs
        )

        self.using_dmpl = using_dmpl
        self.smpl_type = None
        self.generate_skin = generate_skin

        # SMPL-specific data
        self.vertices: np.ndarray = None
        self.kintree_table: np.ndarray = None
        self.bones: np.ndarray = None
        self.weights: np.ndarray = None
        self.faces: np.ndarray = None

        # Load file if provided
        if source_file_path is not None:
            self.load(source_file_path)

    def create_body_element(self, name, pos, joint_type="ball"):
        """Legacy method - kept for compatibility"""
        body = ET.Element('body', name=name, pos=pos)
        ET.SubElement(body, 'joint', type=joint_type)
        ET.SubElement(body, 'geom', size=f"{self.geom_size}", contype="0", conaffinity="0")
        return body

    def build_skeleton(self, parent, relative_jacob, kintree_table, index=0, prefix=None):
        if index >= len(self.joint_names):
            return
        
        joint_name = self.joint_names[index]
        scaled_pos = relative_jacob[index] * self.get_body_ratio(joint_name, prefix=prefix)
        
        # Use base class method to create body with connections
        body = self.create_body_with_joint(
            parent, 
            joint_name, 
            scaled_pos, 
            prefix=prefix, 
            is_root=(index == 0)
        )

        # Recursively build children
        for child_idx in np.where(kintree_table[0] == index)[0]:
            self.build_skeleton(body, relative_jacob, kintree_table, child_idx, prefix=prefix)

    def _generate(self, prefix: str = None):
        # Calculate relative positions between joints
        relative_jacob = self.bones.copy()
        relative_jacob[1:] -= self.bones[self.kintree_table[0, 1:]]

        # Store relative positions in base class structure
        self.joint_positions = [relative_jacob[i] for i in range(len(self.joint_names))]

        worldbody = ET.SubElement(self.xml_root, 'worldbody')
        self.build_skeleton(worldbody, relative_jacob, self.kintree_table, prefix=prefix)

        if self.generate_skin:
            deformable = ET.SubElement(self.xml_root, 'deformable')
            skin = ET.SubElement(deformable, 'skin', attrib=dict(
                rgba="1 1 1 0.5",
                vertex=array_to_string(self.vertices.reshape([-1, ])),
                face=array_to_string(self.faces.reshape([-1, ]))
            ))
            for joint_id in range(self.bones.shape[0]):
                full_weight = self.weights[:, joint_id]
                vertex_ids = np.nonzero(full_weight)[0]
                vertex_weight = full_weight[vertex_ids]
                ET.SubElement(skin, 'bone', attrib=dict(
                    body=get_prefix_name(prefix, self.joint_names[joint_id]),
                    bindpos=array_to_string(self.bones[joint_id]),
                    bindquat="1 0 0 0",
                    vertid=array_to_string(vertex_ids),
                    vertweight=array_to_string(vertex_weight)
                ))

    def _load(self, source_file_path):
        bdata = np.load(source_file_path)
        gender = str(bdata['gender'].astype(str))

        if bdata['poses'].shape[1] == 24 * 3: # SMPL
            self.smpl_type = "smpl"
            with open(osp.join(SMPL_PATH, f"SMPL_{gender.upper()}.pkl"), "rb") as f:
                smpl_dict = pickle.load(f, encoding='latin1')
            self._joint_names = SMPL_JOINT_NAMES
        elif bdata['poses'].shape[1] == 52 * 3 or bdata['poses'].shape[1] == 55 * 3: # SMPLH
            self.smpl_type = "smplh"
            with np.load(osp.join(SMPLH_PATH, gender, "model.npz"), allow_pickle=True) as data:
                smpl_dict = {key: data[key] for key in data.files}
            self._joint_names = SMPLH_JOINT_NAMES
        else:
            raise ValueError("Invalid poses shape")

        vertices = smpl_dict["v_template"] + (smpl_dict["shapedirs"] @ bdata["betas"][:smpl_dict["shapedirs"].shape[2]]).reshape([-1, 3])
        vertices[:, :] = vertices[:, [2, 0, 1]]

        self.vertices = vertices
        self.kintree_table = smpl_dict["kintree_table"]
        self.bones = smpl_dict["J_regressor"] @ vertices
        self.weights = smpl_dict["weights"]
        self.faces = smpl_dict["f"]

        # Set up joint hierarchy for base class
        self.joint_parents = [-1] + self.kintree_table[0, 1:].tolist()
        self.joint_positions = [self.bones[i] for i in range(len(self._joint_names))]

        self.add_scene()
