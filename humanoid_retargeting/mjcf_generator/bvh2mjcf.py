import os.path as osp
import pdb

import numpy as np
import xml.etree.ElementTree as ET

from humanoid_retargeting.mjcf_generator.generator_base import RetargetingMJCFGenerator


class BVH2MJCFGenerator(RetargetingMJCFGenerator):
    def __init__(self, source_file_path, parsing_end=False):
        super().__init__(source_file_path=source_file_path)
        self.parsing_end = parsing_end

        self.lines = None
        self.line_number = None

        self.joint_parents = None
        self.joint_names = None
        self.joint_offsets = None
        self.channels = None

        self.body_element_list = []

    def parse_startswith(self, token):
        assert self.lines[self.line_number].startswith(token)
        self.line_number += 1

    def parse_offset(self):
        assert self.lines[self.line_number].startswith('OFFSET')
        offset = [round(float(x) / 100, 4) for x in self.lines[self.line_number].split()[1:]]
        self.joint_offsets.append(offset)
        self.line_number += 1

    def parse_channels(self):
        assert self.lines[self.line_number].startswith('CHANNELS')
        channels = [x for x in self.lines[self.line_number].split()[2:]]
        self.channels.append(channels)
        self.line_number += 1

    def parse_joint_name(self):
        assert len(self.lines[self.line_number].split()) == 2
        joint_type, joint_name = self.lines[self.line_number].split()
        assert joint_type in ["ROOT", "JOINT"]
        self.joint_names.append(joint_name)
        self.line_number += 1

    def parse_joint(self, parent):
        self.joint_parents.append(parent)
        index = len(self.joint_names)

        self.parse_joint_name()
        self.parse_startswith("{")
        self.parse_offset()
        self.parse_channels()

        while self.lines[self.line_number].startswith(('JOINT', "End")):
            if self.lines[self.line_number].startswith('JOINT'):
                self.parse_joint(index)
            elif self.lines[self.line_number].startswith('End'):
                self.parse_end(index)

        self.parse_startswith("}")

    def parse_end(self, parent):
        if self.parsing_end:
            self.joint_parents.append(parent)
            self.joint_names.append(self.joint_names[parent] + '_bvhend')
            self.line_number += 1
        else:
            self.parse_startswith("End")

        self.parse_startswith("{")

        if self.parsing_end:
            self.parse_offset()
        else:
            self.parse_startswith("OFFSET")

        self.parse_startswith("}")

    def load(self):
        self.lines = []
        for line in open(bvh_file_path, 'r'):
            line = line.strip()
            if line.startswith('MOTION'):
                break
            else:
                self.lines.append(line)

        self.line_number = 0
        self.joint_parents, self.joint_names, self.joint_offsets, self.channels = [], [], [], []

        self.parse_startswith("HIERARCHY")
        self.parse_joint(-1)

        self.joint_offsets = np.array(self.joint_offsets)
        # self.joint_offsets *= 1


    def create_body(self, parent, joint_name, offset):
        if "Upperarm" in joint_name or "Forearm" in joint_name or "Elbow" in joint_name or "Hand" in joint_name:
            scaled_offset = [str(x * 1.35) for x in offset]
        else:
            scaled_offset = [str(x * 0.92) for x in offset]
        body = ET.SubElement(parent, "body", name=joint_name, pos=" ".join(scaled_offset))

        if self.parsing_end and joint_name.endswith("_bvhend"):
            ET.SubElement(body, "geom", type="sphere", size="0.003", rgba="0.2 0.8 0.8 1", contype="0", conaffinity="0")
        else:
            ET.SubElement(body, "joint", name=joint_name, type="ball")
            ET.SubElement(body, "geom", type="sphere", size="0.03", contype="0", conaffinity="0")

        self.body_element_list.append(body)

    def generate(self):
        baselink_elem = ET.SubElement(self.get_elem("worldbody"), "body", attrib={
            "name": self.joint_names[0],
            "pos":" ".join(map(str, self.joint_offsets[0]))
        })
        self.body_element_list.append(baselink_elem)
        ET.SubElement(baselink_elem, "joint", name=self.joint_names[0], type="free")
        ET.SubElement(baselink_elem, "geom", type="sphere", size="0.01", contype="0", conaffinity="0")

        for i, joint_name in enumerate(self.joint_names[1:], start=1):
            parent_body = self.body_element_list[self.joint_parents[i]]
            self.create_body(parent_body, joint_name, self.joint_offsets[i])



if __name__ == '__main__':
    import mujoco
    import mujoco.viewer

    from humanoid_retargeting import BVH_DATA_PATH

    # bvh_file_path = osp.join(BVH_DATA_PATH, "Xingying", "LJJ", 'jj02211-jj.bvh')
    bvh_file_path = osp.join(BVH_DATA_PATH, "Reallusion", "newtaichi", '1_Skill.bvh')

    generator = BVH2MJCFGenerator(bvh_file_path)
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
