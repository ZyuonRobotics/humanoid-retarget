from pathlib import Path

PROJECT_PATH = Path.home() / ".humanoid_retargeting"

GENERATOR_TYPES = ["smpl", "bvh"]

# Data path
DATA_PATH = PROJECT_PATH / "data"
SMPL_DATA_PATH = DATA_PATH / "smpl"
BVH_DATA_PATH = DATA_PATH / "bvh"
GENERATOR_TYPE_TO_DATA_PATH = {
    "smpl": SMPL_DATA_PATH,
    "bvh": BVH_DATA_PATH
}

# Result path
RETARGETING_PATH = PROJECT_PATH / "retargeted"
GENERATOR_TYPE_TO_RETARGETING_PATH = {
    "smpl": RETARGETING_PATH / "smpl",
    "bvh": RETARGETING_PATH / "bvh"
}

# Model path
MODELS_PATH = PROJECT_PATH / "models"
SMPL_PATH = MODELS_PATH / "smpl"
SMPLH_PATH = MODELS_PATH / "smplh"
DMPLS_PATH = MODELS_PATH / "dmpls"

# Config path
CONFIGS_PATH = PROJECT_PATH / "configs"

smpl_model_dict = {}
dmpl_model_dict = {}

# Import body tree utilities
from humanoid_retargeting.mjcf_generator.body_tree import (
    build_body_tree,
    get_human_body_tree,
    get_robot_body_tree,
)

# Import config classes
from humanoid_retargeting.utils.retarget_config import (
    RetargetConfig,
    TrackerConfig,
)

# Import motion player file suffixes
from humanoid_retargeting.motion_player import PLAYER_FILE_SUFFIXES
