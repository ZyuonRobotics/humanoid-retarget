import os.path as osp
import xml.etree.ElementTree as ET
import pickle

import numpy as np

from humanoid_retargeting import SMPL_PATH, SMPLH_PATH
from humanoid_retargeting.mjcf_generator.constants import *
from humanoid_retargeting.mjcf_generator.retargeting_generator_base import RetargetingMJCFGeneratorBase


def array2str(array):
    return " ".join(map(lambda x: str(round(x, 4)), array))

def get_prefix_name(prefix, name):
    return f"{prefix}_{name}" if prefix else name

class SMPL2MJCFGenerator(RetargetingMJCFGeneratorBase):
    generator_type = "smpl"

    def __init__(self, source_file_path, global_body_ratio=1.0, relative_body_ratio_dict=None, using_dmpl=False):
        super().__init__(
            source_file_path=source_file_path,
            global_body_ratio=global_body_ratio,
            relative_body_ratio_dict=relative_body_ratio_dict
        )

        self.using_dmpl = using_dmpl
        self.smpl_type = None

        self._vertices: np.ndarray | None = None
        self._kintree_table: np.ndarray | None = None
        self._bones: np.ndarray | None = None
        self._weights: np.ndarray | None = None
        self._faces: np.ndarray | None = None

    @staticmethod
    def create_body_element(name, pos, joint_type="ball", geom=True):
        body = ET.Element('body', name=name, pos=pos)
        if joint_type:
            ET.SubElement(body, 'joint', type=joint_type)
        if geom:
            ET.SubElement(body, 'geom', size="0.01", contype="0", conaffinity="0")
        return body

    def build_skeleton(self, parent, relative_jacob, kintree_table, index=0, prefix=None):
        if index >= len(self.joint_names):
            return
        joint_name = get_prefix_name(prefix, self.joint_names[index])
        pos = array2str(relative_jacob[index] * self.get_body_ratio(joint_name))
        body = self.create_body_element(joint_name, pos, joint_type="free" if index == 0 else "ball")
        parent.append(body)

        for child_idx in np.where(kintree_table[0] == index)[0]:
            self.build_skeleton(body, relative_jacob, kintree_table, child_idx, prefix=prefix)

    @property
    def vertices(self) -> np.ndarray:
        assert self._vertices is not None, "vertices not loaded, call load() first"
        return self._vertices

    @property
    def kintree_table(self) -> np.ndarray:
        assert self._kintree_table is not None, "kintree_table not loaded, call load() first"
        return self._kintree_table

    @property
    def bones(self) -> np.ndarray:
        assert self._bones is not None, "bones not loaded, call load() first"
        return self._bones

    @property
    def weights(self) -> np.ndarray:
        assert self._weights is not None, "weights not loaded, call load() first"
        return self._weights

    @property
    def faces(self) -> np.ndarray:
        assert self._faces is not None, "faces not loaded, call load() first"
        return self._faces

    def generate(self, prefix: str | None = None):
        relative_jacob = self.bones.copy()
        relative_jacob[1:] -= self.bones[self.kintree_table[0, 1:]]

        worldbody = ET.SubElement(self.xml_root, 'worldbody')
        self.build_skeleton(worldbody, relative_jacob, self.kintree_table, prefix=prefix)

        deformable = ET.SubElement(self.xml_root, 'deformable')
        skin = ET.SubElement(deformable, 'skin', attrib=dict(
            rgba="1 1 1 0.5",
            vertex=array2str(self.vertices.reshape([-1, ])),
            face=array2str(self.faces.reshape([-1, ]))
        ))
        for joint_id in range(self.bones.shape[0]):
            full_weight = self.weights[:, joint_id]
            vertex_ids = np.nonzero(full_weight)[0]
            vertex_weight = full_weight[vertex_ids]
            ET.SubElement(skin, 'bone', attrib=dict(
                body=get_prefix_name(prefix, self.joint_names[joint_id]),
                bindpos=array2str(self.bones[joint_id]),
                bindquat="1 0 0 0",
                vertid=array2str(vertex_ids),
                vertweight=array2str(vertex_weight)
            ))

    def load(self):
        bdata = np.load(self.source_file_path)
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

        self._vertices = vertices
        self._kintree_table = smpl_dict["kintree_table"]
        self._bones = smpl_dict["J_regressor"] @ vertices
        self._weights = smpl_dict["weights"]
        self._faces = smpl_dict["f"]
