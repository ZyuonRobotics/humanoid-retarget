from humanoid_retargeting.mjcf_generator.bvh2mjcf_generator import BVH2MJCFGenerator
from humanoid_retargeting.mjcf_generator.retargeting_generator_base import RetargetingMJCFGeneratorBase
from humanoid_retargeting.mjcf_generator.smpl2mjcf_generator import SMPL2MJCFGenerator

generators = [BVH2MJCFGenerator, SMPL2MJCFGenerator]
generator_class = {g.generator_type: g for g in generators}
