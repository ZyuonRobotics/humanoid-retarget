from typing import List, Union, Optional

import numpy as np
import xml.etree.ElementTree as ET
from hurodes.generators import MJCFGeneratorBase


def get_array_ratio(ratio):
    if isinstance(ratio, float) or isinstance(ratio, int):
        return np.array([ratio] * 3, dtype=np.float32)
    elif isinstance(ratio, list):
        assert len(ratio) == 3
        return np.array(ratio)
    elif isinstance(ratio, np.ndarray):
        assert ratio.shape == (3,)
        return ratio
    else:
        raise ValueError("global_body_ratio must be a float or a list of floats")


def get_prefix_name(prefix, name):
    """Generate prefixed name for joints/bodies"""
    return f"{prefix}_{name}" if prefix else name


def array_to_string(array, precision=4):
    """Convert array to space-separated string with specified precision"""
    return " ".join(map(lambda x: str(round(x, precision)), array))


class RetargetingMJCFGeneratorBase(MJCFGeneratorBase):
    generator_type = "base"

    def __init__(
            self,
            global_body_ratio: Union[float, List[float], np.ndarray] = 1.0,
            relative_body_ratio_dict: Optional[dict] = None,
            geom_size: float = 0.005,
            connection_threshold: float = 0.01,
            generate_connections: bool = True
    ):
        super().__init__()

        self.global_body_ratio = get_array_ratio(global_body_ratio)
        if relative_body_ratio_dict is None:
            self.relative_body_ratio_dict = {}
        else:
            self.relative_body_ratio_dict = {k: get_array_ratio(v) for k, v in relative_body_ratio_dict.items()}

        # Common geometry parameters
        self.geom_size = geom_size
        self.connection_threshold = connection_threshold
        self.generate_connections = generate_connections

        # Common skeletal structure (to be filled by subclasses)
        self._joint_names: list[str] = []
        self.joint_parents: list[int] = []  # parent index for each joint
        self.joint_positions: list[np.ndarray] = []  # absolute or relative positions
        self.body_element_list: list[ET.Element] = []  # for tracking created body elements

    @property
    def joint_names(self):
        return self._joint_names

    def get_body_ratio(self, body_name, prefix=None):
        ratio = self.global_body_ratio.copy()
        # TODO: check if every body_name in self.relative_body_ratio_dict is in self.joint_names
        if prefix is None:
            body_name = body_name
        else:
            body_name = body_name.replace(f"{prefix}_", "")
        if body_name in self.relative_body_ratio_dict:
            ratio *= self.relative_body_ratio_dict[body_name]
        return ratio

    def get_default_geom_attributes(self, geom_type="sphere", size=None):
        """Get default geometry attributes"""
        if size is None:
            size = self.geom_size
        return {
            "contype": "0",
            "conaffinity": "0", 
            "rgba": "0.8 0.8 0.8 1",
            "size": str(size),
            "type": geom_type
        }

    def create_connection_geom(self, parent_element, offset):
        """Create a capsule geometry connecting parent to child joint"""
        if not self.generate_connections:
            return
        
        offset_norm = np.linalg.norm(offset)
        if offset_norm > self.connection_threshold:
            geom_attr = self.get_default_geom_attributes(geom_type="capsule")
            geom_attr.update({
                "fromto": f"0 0 0 {array_to_string(offset)}"
            })
            ET.SubElement(parent_element, "geom", attrib=geom_attr)

    def create_body_with_joint(self, parent_element, joint_name, position, prefix=None, is_root=False):
        """Create a body element with joint and geometry"""
        body_name = get_prefix_name(prefix, joint_name)
        pos_str = array_to_string(position)
        
        # Create connection from parent to this joint
        if not is_root:
            self.create_connection_geom(parent_element, position)
        
        # Create body element
        body = ET.SubElement(parent_element, "body", attrib={
            "name": body_name,
            "pos": pos_str
        })
        
        # Create joint
        joint_type = "free" if is_root else "ball"
        joint_attr = {"type": joint_type}
        if is_root:
            joint_attr["name"] = get_prefix_name(prefix, joint_name)
        else:
            joint_attr["name"] = get_prefix_name(prefix, joint_name)
        ET.SubElement(body, "joint", attrib=joint_attr)
        
        # Create geometry
        geom_attr = self.get_default_geom_attributes()
        if is_root:
            geom_attr["size"] = "0.02"  # Larger size for root
        ET.SubElement(body, "geom", attrib=geom_attr)
        
        self.body_element_list.append(body)
        return body

    def load(self, source_file_path):
        self._loaded = True
        # Reset common structures
        self.body_element_list = []
        self._load(source_file_path)
