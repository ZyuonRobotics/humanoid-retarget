import xml.etree.ElementTree as ET

import numpy as np

from humanoid_retargeting.mjcf_generator.retargeting_generator_base import (
    RetargetingMJCFGeneratorBase, get_prefix_name, array_to_string
)


class BVH2MJCFGenerator(RetargetingMJCFGeneratorBase):
    generator_type = "bvh"

    def __init__(self, source_file_path=None, global_body_ratio=1.0, relative_body_ratio_dict=None, parsing_end=False, **kwargs):
        super().__init__(
            global_body_ratio=global_body_ratio,
            relative_body_ratio_dict=relative_body_ratio_dict,
            **kwargs
        )
        self.parsing_end = parsing_end

        # BVH-specific parsing state
        self.lines: list[str] = []
        self.line_number: int = 0
        self.joint_offsets: list[list[float]] = []
        self.channels: list[list[str]] = []

        # Load file if provided
        if source_file_path is not None:
            self.load(source_file_path)

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
        self._joint_names.append(joint_name)
        self.line_number += 1

    def parse_joint(self, parent):
        self.joint_parents.append(parent)
        index = len(self._joint_names)

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
            self._joint_names.append(self._joint_names[parent] + '_bvhend')
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

        # Reset parsing state
        self.line_number = 0
        self.joint_parents, self._joint_names, self.joint_offsets, self.channels = [], [], [], []

        self.parse_startswith("HIERARCHY")
        self.parse_joint(-1)

        # Set up joint_positions for base class (convert offsets to numpy arrays)
        self.joint_positions = [np.array(offset) for offset in self.joint_offsets]

    def create_body(self, parent, joint_name, offset, prefix=None):
        """Legacy method for creating body with BVH-specific behavior"""
        # Scale offset by body ratio
        scaled_offset = offset * self.get_body_ratio(joint_name, prefix=prefix)
        
        # Use base class method for standard body creation
        body = self.create_body_with_joint(parent, joint_name, scaled_offset, prefix=prefix)

        # Handle BVH-specific end joint behavior
        if self.parsing_end and joint_name.endswith("_bvhend"):
            # Remove the joint for end effectors and keep only geometry
            joints = body.findall('joint')
            for joint in joints:
                body.remove(joint)

        return body

    def _generate(self, prefix: str = None):
        # Create root body using base class method
        scaled_root_offset = self.joint_positions[0] * self.get_body_ratio(self._joint_names[0], prefix=prefix)
        root_body = self.create_body_with_joint(
            self.get_elem("worldbody"), 
            self._joint_names[0], 
            scaled_root_offset, 
            prefix=prefix, 
            is_root=True
        )

        # Create child bodies
        for i, joint_name in enumerate(self._joint_names[1:], start=1):
            parent_body = self.body_element_list[self.joint_parents[i]]
            self.create_body(parent_body, joint_name, self.joint_positions[i], prefix=prefix)
        
        self.add_scene()
