import xml.etree.ElementTree as ET

from hurodes.generators import MJCFHumanoidGenerator

def get_prefix_name(prefix, name):
    return f"{prefix}_{name}" if prefix else name

class TrackerMJCFGenerator(MJCFHumanoidGenerator):
    def __init__(self, tracker_dict, tracker_offset):
        super().__init__()

        assert len(tracker_offset) > 0, "tracker_offset should not be empty"

        self.tracker_dict = tracker_dict
        self.tracker_offset = tracker_offset

    def generate_single_body_xml(self, parent_node, body_idx, prefix):
        body_elem = super().generate_single_body_xml(parent_node, body_idx, prefix=prefix)

        for group_name, offset_list in self.tracker_offset.items():
            for human_body_name, robot_body_name, offset in zip(
                    self.tracker_dict[group_name].human,
                    self.tracker_dict[group_name].robot,
                    offset_list
            ):
                if body_elem.attrib['name'] == get_prefix_name(prefix, robot_body_name):
                    site_elem = ET.SubElement(body_elem, 'site', attrib={
                        "name": f"{robot_body_name}_{human_body_name}_tracker",
                        "pos": " ".join(map(str, offset[:3].tolist())),
                        "quat": " ".join(map(str, offset[3:].tolist()))
                    })
        return body_elem
