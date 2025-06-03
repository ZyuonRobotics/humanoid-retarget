
import numpy as np
from scipy.signal import butter, filtfilt
from scipy.spatial.transform import Rotation



def filter_lowpass2d(data, frame_rate, cutoff=20, order=2):
    assert len(data.shape) == 2

    nyq = 0.5 * frame_rate
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    filtered = np.zeros_like(data)
    for i in range(data.shape[1]):
        filtered[:, i] = filtfilt(b, a, data[:, i])
    return filtered


def filter_lowpass_quaternion(quat, frame_rate, cutoff=20, order=2):
    assert len(quat.shape) == 2 and quat.shape[1] == 4

    rotvec = Rotation.from_quat(quat[:, [1, 2, 3, 0]]).as_rotvec()
    lowpass_filter_rotvec = filter_lowpass2d(rotvec, frame_rate, cutoff, order)
    filtered_quat = Rotation.from_rotvec(lowpass_filter_rotvec).as_quat()[:, [3, 0, 1, 2]]
    return filtered_quat