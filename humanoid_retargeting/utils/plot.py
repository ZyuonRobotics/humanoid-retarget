import matplotlib.pyplot as plt


def plot2d(array, dim_label=None, view=True):
    if dim_label is None:
        dim_label = [f"dim{i}" for i in range(array.shape[1])]
    for i, label in zip(range(array.shape[1]), dim_label):
        plt.plot(array[:, i], label=label)
    plt.legend()
    if view:
        plt.show()