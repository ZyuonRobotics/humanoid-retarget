from pathlib import Path
import xml.etree.ElementTree as ET
import pickle

import numpy as np

from humanoid_retargeting import SMPL_PATH, SMPLH_PATH
from humanoid_retargeting.mjcf_generator.constants import *
from humanoid_retargeting.mjcf_generator.retargeting_generator_base import RetargetingMJCFGeneratorBase


class SMPL2MJCFGenerator(RetargetingMJCFGeneratorBase):
    generator_type = "smpl"

    def __init__(
        self, 
        global_body_ratio=1.0, 
        relative_body_ratio_dict=None,
        using_dmpl=False,
        geom_size=0.01,
        generate_skin=True,
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

        self.skin_params = None

    def _clean(self):
        super()._clean()
        self.skin_params = None
    
    def _generate(self, prefix: str = None, add_scene=True, **kwargs):
        super()._generate(prefix, add_scene, **kwargs)

        if self.generate_skin:
            deformable = ET.SubElement(self.xml_root, 'deformable')
            skin = ET.SubElement(deformable, 'skin', attrib=dict(
                rgba="1 1 1 0.5",
                vertex=self.array_to_string(self.skin_params["vertices"].reshape([-1, ])),
                face=self.array_to_string(self.skin_params["faces"].reshape([-1, ]))
            ))
            for joint_id in range(self.skin_params["joint_positions"].shape[0]):
                full_weight = self.skin_params["weights"][:, joint_id]
                vertex_ids = np.nonzero(full_weight)[0]
                vertex_weight = full_weight[vertex_ids]
                ET.SubElement(skin, 'bone', attrib=dict(
                    body=self.get_prefix_name(prefix, self.joint_names[joint_id]),
                    bindpos=self.array_to_string(self.skin_params["joint_positions"][joint_id]),
                    bindquat="1 0 0 0",
                    vertid=self.array_to_string(vertex_ids),
                    vertweight=self.array_to_string(vertex_weight)
                ))

    def _load(self, source_file_path):
        bdata = np.load(source_file_path)
        gender = str(bdata['gender'].astype(str))

        if bdata['poses'].shape[1] == 24 * 3: # SMPL
            self.smpl_type = "smpl"
            with open(Path(SMPL_PATH) / f"SMPL_{gender.upper()}.pkl", "rb") as f:
                smpl_dict = pickle.load(f, encoding='latin1')
            self.joint_names = SMPL_JOINT_NAMES
        elif bdata['poses'].shape[1] == 52 * 3 or bdata['poses'].shape[1] == 55 * 3: # SMPLH
            self.smpl_type = "smplh"
            with np.load(Path(SMPLH_PATH) / gender / "model.npz", allow_pickle=True) as data:
                smpl_dict = {key: data[key] for key in data.files}
            self.joint_names = SMPLH_JOINT_NAMES
        else:
            raise ValueError("Invalid poses shape")


        # kintree_table is exactly the same as joint_parents, except for the first joint
        self.joint_parents = smpl_dict["kintree_table"][0].astype(int)
        self.joint_parents[0] = -1

        vertices = smpl_dict["v_template"] + (smpl_dict["shapedirs"] @ bdata["betas"][:smpl_dict["shapedirs"].shape[2]]).reshape([-1, 3])
        vertices[:, :] = vertices[:, [2, 0, 1]]
        joint_positions = smpl_dict["J_regressor"] @ vertices

        self.joint_offsets = joint_positions.copy()
        self.joint_offsets[1:] -= joint_positions[self.joint_parents[1:]]

        if self.generate_skin: # load skin params
            # Apply global_body_ratio to scale skin vertices and joint positions
            scaled_vertices = vertices * self.global_body_ratio
            scaled_joint_positions = joint_positions * self.global_body_ratio

            self.skin_params = {
                "vertices": scaled_vertices,
                "weights": smpl_dict["weights"],
                "faces": smpl_dict["f"],
                "joint_positions": scaled_joint_positions
            }
