import matplotlib.pyplot as plt
import numpy as np

def plot2d(array: np.ndarray, dim_label: list[str] = None, view: bool = True):
    if dim_label is None:
        dim_label = [f"dim{i}" for i in range(array.shape[1])]
    for i, label in zip(range(array.shape[1]), dim_label):
        plt.plot(array[:, i], label=label)
    plt.legend()
    if view:
        plt.show()