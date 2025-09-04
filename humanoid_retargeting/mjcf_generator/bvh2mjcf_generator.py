import xml.etree.ElementTree as ET

import numpy as np

from humanoid_retargeting.mjcf_generator.retargeting_generator_base import RetargetingMJCFGeneratorBase

class BVH2MJCFGenerator(RetargetingMJCFGeneratorBase):
    generator_type = "bvh"

    def __init__(self, global_body_ratio=1.0, relative_body_ratio_dict=None, parsing_end=False, **kwargs):
        super().__init__(
            global_body_ratio=global_body_ratio,
            relative_body_ratio_dict=relative_body_ratio_dict,
            **kwargs
        )
        self.parsing_end = parsing_end

        # BVH-specific parsing state
        self.lines: list[str] = []
        self.line_number: int = 0
        self.channels: list[list[str]] = []

        self.body_element_list = []


    def _clean(self):
        super()._clean()
        self.lines = []
        self.line_number = 0
        self.channels = []
        
    def _destroy(self):
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

    def _load(self, source_file_path):
        # Parse BVH file
        self.lines = []
        for line in open(source_file_path, 'r'):
            line = line.strip()
            if line.startswith('MOTION'):
                break
            else:
                self.lines.append(line)

        self.joint_offsets, self.joint_parents = [], []
        self.parse_startswith("HIERARCHY")
        self.parse_joint(-1)
        self.joint_offsets, self.joint_parents = np.array(self.joint_offsets), np.array(self.joint_parents)
