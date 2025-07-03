import xml.etree.ElementTree as ET

import numpy as np

from humanoid_retargeting.mjcf_generator.retargeting_generator_base import RetargetingMJCFGeneratorBase

def get_prefix_name(prefix, name):
    return f"{prefix}_{name}" if prefix else name


class BVH2MJCFGenerator(RetargetingMJCFGeneratorBase):
    generator_type = "bvh"

    def __init__(self, source_file_path, global_body_ratio=1.0, relative_body_ratio_dict=None, parsing_end=False):
        super().__init__(
            source_file_path=source_file_path,
            global_body_ratio=global_body_ratio,
            relative_body_ratio_dict=relative_body_ratio_dict
        )
        self.parsing_end = parsing_end

        self.lines: list[str] = []
        self.line_number: int = 0

        self.joint_parents: list[int] = []
        self.joint_names: list[str] = []
        self.joint_offsets: list[list[float]] = []
        self.channels: list[list[str]] = []

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
        for line in open(self.source_file_path, 'r'):
            line = line.strip()
            if line.startswith('MOTION'):
                break
            else:
                self.lines.append(line)

        self.line_number = 0
        self.joint_parents, self.joint_names, self.joint_offsets, self.channels = [], [], [], []

        self.parse_startswith("HIERARCHY")
        self.parse_joint(-1)

    def create_body(self, parent, joint_name, offset, prefix=None):
        default_geom_attr = {"contype": "0", "conaffinity": "0", "rgba": "0.8 0.8 0.8 1", "size": "0.005",
                             "type": "sphere"}
        if np.linalg.norm(offset) > 0.01:
            ET.SubElement(parent, "geom", attrib=default_geom_attr | {
                "type": "capsule",
                "fromto": "0 0 0 " + " ".join(map(str, offset))
            })
        body = ET.SubElement(parent, "body", attrib={"name": get_prefix_name(prefix, joint_name), "pos": " ".join(map(str, offset))})

        if self.parsing_end and joint_name.endswith("_bvhend"):
            ET.SubElement(body, "geom", attrib=default_geom_attr)
        else:
            ET.SubElement(body, "joint", attrib={"name": get_prefix_name(prefix, joint_name), "type": "ball"})
            ET.SubElement(body, "geom", attrib=default_geom_attr)

        self.body_element_list.append(body)

    def generate(self, prefix: str | None = None):
        baselink_elem = ET.SubElement(self.get_elem("worldbody"), "body", attrib={
            "name": get_prefix_name(prefix, self.joint_names[0]),
            "pos": " ".join(map(str, self.joint_offsets[0] * self.get_body_ratio(self.joint_names[0])))
        })
        self.body_element_list.append(baselink_elem)
        ET.SubElement(baselink_elem, "joint", name=self.joint_names[0], type="free")
        ET.SubElement(baselink_elem, "geom", type="sphere", size="0.02", contype="0", conaffinity="0")

        for i, joint_name in enumerate(self.joint_names[1:], start=1):
            parent_body = self.body_element_list[self.joint_parents[i]]
            self.create_body(parent_body, joint_name, self.joint_offsets[i] * self.get_body_ratio(joint_name), prefix=prefix)
