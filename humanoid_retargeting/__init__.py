from pathlib import Path

PROJECT_PATH = Path.home() / ".humanoid_retargeting"

DATA_PATH = PROJECT_PATH / "data"
SMPL_DATA_PATH = DATA_PATH / "smpl"
BVH_DATA_PATH = DATA_PATH / "bvh"

MODELS_PATH = PROJECT_PATH / "models"
SMPL_PATH = MODELS_PATH / "smpl"
SMPLH_PATH = MODELS_PATH / "smplh"
DMPLS_PATH = MODELS_PATH / "dmpls"

PARAMETERS_PATH = PROJECT_PATH / "parameters"

smpl_model_dict = {}
dmpl_model_dict = {}
