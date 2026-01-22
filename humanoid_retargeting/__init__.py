from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data"

GENERATOR_TYPES = ["smpl", "bvh"]

# Data path
MOCAP_DATA_PATH = DATA_PATH / "mocap"
SMPL_DATA_PATH = MOCAP_DATA_PATH / "smpl"
BVH_DATA_PATH = MOCAP_DATA_PATH / "bvh"
GENERATOR_TYPE_TO_DATA_PATH = {
    "smpl": SMPL_DATA_PATH,
    "bvh": BVH_DATA_PATH
}

# Result path
RETARGETING_PATH = DATA_PATH / "retargeted"
GENERATOR_TYPE_TO_RETARGETING_PATH = {
    "smpl": RETARGETING_PATH / "smpl",
    "bvh": RETARGETING_PATH / "bvh"
}

# Model path
MODELS_PATH = DATA_PATH / "models"
SMPL_PATH = MODELS_PATH / "smpl"
SMPLH_PATH = MODELS_PATH / "smplh"
DMPLS_PATH = MODELS_PATH / "dmpls"

# Config path
CONFIGS_PATH = DATA_PATH / "configs"

smpl_model_dict = {}
dmpl_model_dict = {}
