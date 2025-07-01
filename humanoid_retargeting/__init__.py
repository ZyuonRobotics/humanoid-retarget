from pathlib import Path

PROJECT_PATH = Path.home() / ".humanoid_retargeting"

DATA_PATH = PROJECT_PATH / "data"
AMASS_DATA_PATH = DATA_PATH / "amass"
BVH_DATA_PATH = DATA_PATH / "bvh"

MODELS_PATH = PROJECT_PATH / "models"
SMPLH_PATH = MODELS_PATH / "smplh"
DMPLS_PATH = MODELS_PATH / "dmpls"

PARAMETERS_PATH = PROJECT_PATH / "parameters"

smpl_model_dict = {}
dmpl_model_dict = {}

try:
    import numpy as np

    for gender in ["male", "female", "neutral"]:
        smpl_model_file = SMPLH_PATH / gender / "model.npz"
        dmpl_model_file = DMPLS_PATH / gender / "model.npz"

        if smpl_model_file.exists():
            with np.load(str(smpl_model_file), allow_pickle=True) as data:
                smpl_model_dict[gender] = {key: data[key] for key in data.files}

        if dmpl_model_file.exists():
            with np.load(str(dmpl_model_file), allow_pickle=True) as data:
                dmpl_model_dict[gender] = {key: data[key] for key in data.files}

except Exception as e:
    print(f"Error loading SMPLH and DMPLS models: {e}")
