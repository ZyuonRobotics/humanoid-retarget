from typing import List, Union, Optional

import numpy as np
from hurodes.mjcf_generator.generator_base import MJCFGeneratorBase


def get_array_ratio(ratio):
    if isinstance(ratio, float):
        return np.array([ratio] * 3)
    elif isinstance(ratio, list):
        assert len(ratio) == 3
        return np.array(ratio)
    elif isinstance(ratio, np.ndarray):
        assert ratio.shape == (3,)
        return ratio
    else:
        raise ValueError("global_body_ratio must be a float or a list of floats")


class RetargetingMJCFGeneratorBase(MJCFGeneratorBase):
    generator_type = "base"

    def __init__(
            self,
            source_file_path: str,
            global_body_ratio: Union[float, List[float], np.ndarray] = 1.0,
            relative_body_ratio_dict: Optional[dict] = None
    ):
        super().__init__(disable_gravity=True)

        self.source_file_path = source_file_path

        self.global_body_ratio = get_array_ratio(global_body_ratio)
        if relative_body_ratio_dict is None:
            self.relative_body_ratio_dict = {}
        else:
            self.relative_body_ratio_dict = {k: get_array_ratio(v) for k, v in relative_body_ratio_dict.items()}

    def get_body_ratio(self, body_name):
        ratio = self.global_body_ratio.copy()
        if body_name in self.relative_body_ratio_dict:
            ratio *= self.relative_body_ratio_dict[body_name]
        return ratio
