from typing import List, Union, Optional

import numpy as np
import xml.etree.ElementTree as ET
from hurodes.mjcf_generator.unified_generator import UnifiedMJCFGenerator

class TrackerMJCFGenerator(UnifiedMJCFGenerator):
    def __init__(self, ehdf_path, tracker_dict, tracker_offset):
        super().__init__(ehdf_path=ehdf_path)

        assert len(tracker_offset) > 0, "tracker_offset should not be empty"

        self.tracker_dict = tracker_dict
        self.tracker_offset = tracker_offset

    def generate_single_body_xml(self, parent_node, body_idx):
        body_elem = super().generate_single_body_xml(parent_node, body_idx)

        for group_name, offset_list in self.tracker_offset.items():
            for human_body_name, robot_body_name, offset in zip(
                    self.tracker_dict[group_name].human,
                    self.tracker_dict[group_name].robot,
                    offset_list
            ):
                if body_elem.attrib['name'] == robot_body_name:
                    site_elem = ET.SubElement(body_elem, 'site', attrib={
                        "name": f"{robot_body_name}_{human_body_name}_tracker",
                        "pos": " ".join(map(str, offset[:3].tolist())),
                        "quat": " ".join(map(str, offset[3:].tolist()))
                    })
        return body_elem

