from scipy.spatial.transform import Rotation

def euler2quat(x, y, z):
    rot = Rotation.from_euler('xyz', [x, y, z], degrees=True)
    return rot.as_quat()[[3, 0, 1, 2]]