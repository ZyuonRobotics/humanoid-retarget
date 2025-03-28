from abc import ABC, abstractmethod

import xml.etree.ElementTree as ET

from hurodes.mjcf_generator.generator_base import MJCFGeneratorBase
from hurodes.mjcf_generator.default_attrs import *


class RetargetingMJCFGenerator(MJCFGeneratorBase):
    def __init__(self, source_file_path):
        super().__init__(disable_gravity=True)

        self.source_file_path = source_file_path

    def add_scene(self):
        # visual
        visual_elem = self.get_elem("visual")
        headlight_elem = ET.SubElement(visual_elem, 'headlight',
                                       attrib={"diffuse": "0.6 0.6 0.6", "ambient": "0.3 0.3 0.3", "specular": "0 0 0"})
        rgba_elem = ET.SubElement(visual_elem, 'rgba', attrib={"haze": "0.15 0.25 0.35 1"})
        global_elem = ET.SubElement(visual_elem, 'global', attrib={"azimuth": "160", "elevation": "-20"})

        # asset
        asset_elem = self.get_elem("asset")
        ET.SubElement(asset_elem, "texture", attrib=DEFAULT_SKY_TEXTURE_ATTR)
        ET.SubElement(asset_elem, "texture", attrib=DEFAULT_GROUND_TEXTURE_ATTR)
        ET.SubElement(asset_elem, "material", attrib=DEFAULT_GROUND_MATERIAL_ATTR)

        worldbody_elem = self.get_elem("worldbody")
        light = ET.SubElement(worldbody_elem, 'light', attrib=DEFAULT_SKY_LIGHT_ATTR)
        geom = ET.SubElement(worldbody_elem, 'geom', attrib=DEFAULT_GROUND_GEOM_ATTR)