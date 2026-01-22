import matplotlib.pyplot as plt
import numpy as np

def plot2d(array: np.ndarray, dim_label: list[str] = None, view: bool = True):
    if dim_label is None:
        dim_label = [f"dim{i}" for i in range(array.shape[1])]

    n_dims = array.shape[1]
    fig, axes = plt.subplots(n_dims, 1, figsize=(10, 3 * n_dims), sharex=True)
    if n_dims == 1:
        axes = [axes]

    for i, (ax, label) in enumerate(zip(axes, dim_label)):
        ax.plot(array[:, i], label=label)
        ax.set_ylabel(label)
        ax.legend(loc='upper right')
        ax.grid(True)

    axes[-1].set_xlabel('Frame')
    plt.tight_layout()
    if view:
        plt.show()
    else:
        plt.close(fig)