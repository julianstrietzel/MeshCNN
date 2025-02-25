import os
import pickle
import warnings

import numpy as np
import torch.utils.data as data


class BaseDataset(data.Dataset):
    def __init__(self, opt):
        self.opt = opt
        self.mean = 0
        self.std = 1
        self.ninput_channels = None
        super(BaseDataset, self).__init__()

    def get_mean_std(self):
        """Computes Mean and Standard Deviation from Training Data
        If mean/std file doesn't exist, will compute one
        :returns
        mean: N-dimensional mean
        std: N-dimensional standard deviation
        ninput_channels: N
        (here N=5)
        """

        mean_std_cache = os.path.join(self.root, "mean_std_cache.p")
        if not os.path.exists(self.root):
            mean_std_cache = os.path.join(
                os.path.dirname(self.paths[0][0]), "mean_std_cache.p",
            )

        # TODO: Potentially it could be an issue that while we normalize our bacon_meshes one by one, we compute the
        #  mean and std over all the meshcnn meshes. This will potentially lead to a different normalization and issues
        #  when generalizing over multiple objects in one dataset.
        if not os.path.isfile(mean_std_cache) or True:
            # TODO remove the or True for caching efficiency
            print("computing mean std from train data...")
            # doesn't run augmentation during m/std computation
            num_aug = self.opt.num_aug
            self.opt.num_aug = 1
            mean, std = np.array(0), np.array(0)
            for i, data in enumerate(self):
                if i == self.size:
                    i = self.size - 1
                    break
                if i % 500 == 0:
                    print("{} of {}".format(i, self.size))
                features = data["edge_features"]
                mean = mean + features.mean(axis=1)
                std = std + features.std(axis=1)
            mean = mean / (i + 1)
            std = std / (i + 1)
            transform_dict = {
                "mean": mean[:, np.newaxis],
                "std": std[:, np.newaxis],
                "ninput_channels": len(mean),
            }
            with open(mean_std_cache, "wb") as f:
                pickle.dump(transform_dict, f)
            print("saved: ", mean_std_cache)
            self.opt.num_aug = num_aug
        else:
            warnings.warn("Using cached mean / std from {}".format(mean_std_cache))
        # open mean / std from file
        with open(mean_std_cache, "rb") as f:
            transform_dict = pickle.load(f)
            self.mean = transform_dict["mean"]
            self.std = transform_dict["std"]
            self.ninput_channels = transform_dict["ninput_channels"]
        self.mean_defined = True


def collate_fn(batch):
    """Creates mini-batch tensors
    We should build custom collate_fn rather than using default collate_fn
    """
    meta = {}
    keys = batch[0].keys()
    for key in keys:
        meta.update({key: np.array([d[key] for d in batch])})
    return meta
