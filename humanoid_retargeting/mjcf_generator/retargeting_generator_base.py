from typing import List, Union, Optional

import numpy as np
import xml.etree.ElementTree as ET
from hurodes.generators import MJCFGeneratorBase

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

        self.global_body_ratio = self.get_array_ratio(global_body_ratio)
        if relative_body_ratio_dict is None:
            self.relative_body_ratio_dict = {}
        else:
            self.relative_body_ratio_dict = {k: self.get_array_ratio(v) for k, v in relative_body_ratio_dict.items()}

        self.geom_size = geom_size
        self.connection_threshold = connection_threshold
        self.generate_connections = generate_connections

        self.joint_names: list[str] = []
        self.joint_parents: np.ndarray = None # parent index for each joint
        self.joint_offsets: np.ndarray = None  # relative positions of parent joints

    def _clean(self):
        self.joint_names = []
        self.joint_parents = None
        self.joint_offsets = None

    def _destroy(self):
        pass

    @classmethod
    def from_source_file_path(cls, source_file_path, **kwargs):
        generator = cls(**kwargs)
        generator.load(source_file_path)
        return generator

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

    def get_geom_attributes(self, geom_type="sphere", size=None, offset=None):
        """Get default geometry attributes"""
        attrs = {"contype": "0", "conaffinity": "0",  "rgba": "0.8 0.8 0.8 1", "type": geom_type}
        size = self.geom_size if size is None else size
        attrs["size"] = str(size)
        if geom_type == "capsule":
            assert offset is not None
            attrs["fromto"] = f"0 0 0 {self.array_to_string(offset)}"
        return attrs

    def create_connection_geom(self, parent_element, offset):
        """Create a capsule geometry connecting parent to child joint"""
        if not self.generate_connections:
            return
        
        offset_norm = np.linalg.norm(offset)
        if offset_norm > self.connection_threshold:
            geom_attr = self.get_geom_attributes(geom_type="capsule", offset=offset)
            ET.SubElement(parent_element, "geom", attrib=geom_attr)

    def create_body_with_joint(self, parent_element, joint_name, position, prefix=None, is_root=False):
        """Create a body element with joint and geometry"""
        if not is_root:
            self.create_connection_geom(parent_element, position)
        
        body_elem = ET.SubElement(parent_element, "body", attrib={
            "name": self.get_prefix_name(prefix, joint_name),
            "pos": self.array_to_string(position)
        })
        
        ET.SubElement(body_elem, "joint", attrib={
            "type": "free" if is_root else "ball",
            "name": self.get_prefix_name(prefix, joint_name)
        })
        
        ET.SubElement(body_elem, "geom", attrib=self.get_geom_attributes())
        
        return body_elem

    def build_skeleton(self, parent, joint_idx, prefix=None):
        if joint_idx >= len(self.joint_names):
            return
        
        joint_name = self.joint_names[joint_idx]
        scaled_pos = self.joint_offsets[joint_idx] * self.get_body_ratio(joint_name, prefix=prefix)
        
        body = self.create_body_with_joint(parent, joint_name, scaled_pos, prefix=prefix, is_root=(joint_idx == 0))

        # Recursively build children
        for child_idx in np.where(self.joint_parents == joint_idx)[0]:
            self.build_skeleton(body, child_idx, prefix)

    def load(self, source_file_path):
        self._load(source_file_path)
        self._loaded = True

    def _generate(self, prefix: str = None, add_scene=True, **kwargs):
        self.build_skeleton(self.get_elem("worldbody"), joint_idx=0, prefix=prefix)
        if add_scene:
            self.add_scene()


    @staticmethod
    def get_prefix_name(prefix, name):
        """Generate prefixed name for joints/bodies"""
        return f"{prefix}_{name}" if prefix else name

    @staticmethod
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

    @staticmethod
    def array_to_string(array, precision=4):
        """Convert array to space-separated string with specified precision"""
        return " ".join(map(lambda x: str(round(x, precision)), array))

