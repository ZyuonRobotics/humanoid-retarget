from os import path

DATA_PATH = path.expanduser("~/.retargeting")
AMASS_DATA_PATH = path.join(DATA_PATH, "amass_data")
BVH_DATA_PATH = path.join(DATA_PATH, "bvh_data")

SMPLH_PATH = path.join(DATA_PATH, "smpl_models", "smplh")
DMPLS_PATH = path.join(DATA_PATH, "smpl_models", "dmpls")

smpl_model_dict = {}
dmpl_model_dict = {}

try:
    import numpy as np
    for gender in ["male", "female", "neutral"]:
        with np.load(path.join(SMPLH_PATH, gender, "model.npz"), allow_pickle=True) as data:
            smpl_model_dict[gender] = {key: data[key] for key in data.files}
        with np.load(path.join(DMPLS_PATH, gender, "model.npz"), allow_pickle=True) as data:
            dmpl_model_dict[gender] = {key: data[key] for key in data.files}
except Exception as e:
    print(f"Error loading SMPLH and DMPLS models: {e}")
