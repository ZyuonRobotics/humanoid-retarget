from abc import ABC, abstractmethod

import xml.etree.ElementTree as ET
import numpy as np
from hurodes.mjcf_generator.generator_base import MJCFGeneratorBase


class RetargetingMJCFGeneratorBase(MJCFGeneratorBase):
    generator_type = "base"
    def __init__(self, source_file_path, whole_body_ratio=1.0, body_ratio_dict=None):
        super().__init__(disable_gravity=True)

        self.source_file_path = source_file_path
        self.whole_body_ratio = whole_body_ratio
        self.body_ratio_dict = body_ratio_dict or {}

    def get_body_ratio(self, body_name):
        ratio = self.body_ratio_dict.get(body_name, self.whole_body_ratio)
        if isinstance(ratio, float) or isinstance(ratio, int):
            return np.array([ratio, ratio, ratio])
        elif isinstance(ratio, list):
            assert len(ratio) == 3
            return np.array(ratio)
        else:
            raise ValueError(f"Invalid ratio for body {body_name}: {ratio}")
