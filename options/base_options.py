import argparse
import datetime
import os
import warnings

import torch

from util import util

time_s = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


class BaseOptions:
    EXTRACTOR_CLASS = "MeshCNN"

    def __init__(self):
        self.parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        self.initialized = False
        self.is_train = False

    def initialize(self):
        # data params
        self.parser.add_argument(
            "--dataroot",
            required=True,
            help="path to meshes (should have subfolders train, test)",
        )
        self.parser.add_argument(
            "--dataset_mode",
            choices={"classification", "segmentation", "regression"},
            default="classification",
        )
        self.parser.add_argument(
            "--ninput_edges",
            type=int,
            default=750,
            help="# of input edges (will include dummy edges)",
        )
        self.parser.add_argument(
            "--max_dataset_size",
            type=int,
            default=float("inf"),
            help="Maximum number of samples per epoch",
        )
        # network params
        self.parser.add_argument(
            "--batch_size", type=int, default=16, help="input batch size"
        )
        self.parser.add_argument(
            "--arch", type=str, default="mconvnet", help="selects network to use"
        )  # todo add choices
        self.parser.add_argument(
            "--resblocks", type=int, default=1, help="# of res blocks"
        )
        self.parser.add_argument(
            "--fc_n", type=int, default=100, help="# between fc and nclasses"
        )  # todo make generic
        self.parser.add_argument(
            "--ncf", nargs="+", default=[16, 32, 32], type=int, help="conv filters"
        )
        self.parser.add_argument(
            "--pool_res",
            nargs="+",
            default=[1140, 780, 580],
            type=int,
            help="pooling res",
        )
        self.parser.add_argument(
            "--norm",
            type=str,
            default="batch",
            help="instance normalization or batch normalization or group normalization",
        )
        self.parser.add_argument(
            "--num_groups", type=int, default=16, help="# of groups for groupnorm"
        )
        self.parser.add_argument(
            "--init_type",
            type=str,
            default="normal",
            help="network initialization [normal|xavier|kaiming|orthogonal]",
        )
        self.parser.add_argument(
            "--init_gain",
            type=float,
            default=0.02,
            help="scaling factor for normal, xavier and orthogonal.",
        )
        # general params
        self.parser.add_argument(
            "--num_threads", default=1, type=int, help="# threads for loading data"
        )
        self.parser.add_argument(
            "--gpu_ids",
            type=str,
            default="0",
            help="gpu ids: e.g. 0  0,1,2, 0,2. use -1 for CPU",
        )
        self.parser.add_argument(
            "--name",
            type=str,
            default="debug",
            help="name of the experiment. It decides where to store samples and models",
        )
        self.parser.add_argument(
            "--checkpoints_dir",
            type=str,
            default="./checkpoints",
            help="models are saved here",
        )
        self.parser.add_argument(
            "--serial_batches",
            action="store_true",
            help="if true, takes meshes in order, otherwise takes them randomly",
        )
        self.parser.add_argument("--seed", type=int, help="if specified, uses seed")
        # visualization params
        self.parser.add_argument(
            "--export_folder",
            type=str,
            default="",
            help="exports intermediate collapses to this folder",
        )
        #
        # sdf_regressino arguments
        self.parser.add_argument(
            "--point_encode",
            type=str,
            default="no_encode",
            help="point encoding method from no_encdoe or positional_encoding_3d",
        )
        self.parser.add_argument(
            "--include_input_in_encoding",
            type=bool,
            default=True,
            help="Whether to include the input coords in the point encoding",
        )
        self.parser.add_argument(
            "--num_freqs",
            type=int,
            default=2,
            help="number of frequencies to use in positional encoding",  #
        )
        self.parser.add_argument(
            "--normalize_mesh",
            action="store_true",
            default=False,
            help="Whether to normalize the mesh like bacon",
        )
        self.parser.add_argument(
            "--normalize_features",
            action="store_true",
            default=False,
            help="Whether to normalize the edge features in meshcnn meshes using std and mean",
        )

        self.parser.add_argument(
            "--loss", type=str, default="mse", help="loss function to use",
        )
        self.parser.add_argument(
            "--loss_alpha",
            type=float,
            default=0.5,
            help="alpha param for loss function",
        )

        self.parser.add_argument(
            "--relu_deactivated",
            action="store_true",
            default=False,
            help="Whether to deactivate relu in the convolutionals within the network. Default is False, deactivation is recommended for regression.",
        )
        self.parser.add_argument(
            "--pretrained_path",
            type=str,
            default="",
            help="pre-trained model path can be found at ./checkpoints/shrec16/pre_trained_removed_layers.pth",
        )
        self.initialized = True

    def parse(self):
        if not self.initialized:
            self.initialize()
        self.opt, unknown = self.parser.parse_known_args()
        self.opt.is_train = self.is_train  # train or test
        if unknown:
            warnings.warn("unknown arguments:")
            print(unknown)
        str_ids = self.opt.gpu_ids.split(",")
        self.opt.gpu_ids = []
        for str_id in str_ids:
            id = int(str_id)
            if id >= 0:
                self.opt.gpu_ids.append(id)
        # set gpu ids
        if len(self.opt.gpu_ids) > 0:
            torch.cuda.set_device(self.opt.gpu_ids[0])

        args = vars(self.opt)

        if self.opt.seed is not None:
            import numpy as np
            import random

            torch.manual_seed(self.opt.seed)
            np.random.seed(self.opt.seed)
            random.seed(self.opt.seed)

        if self.opt.export_folder:
            self.opt.export_folder = os.path.join(
                self.opt.checkpoints_dir, self.opt.name, self.opt.export_folder
            )
            util.mkdir(self.opt.export_folder)
        expr_dir = os.path.join(
            self.opt.checkpoints_dir,
            self.opt.name,
            time_s if self.is_train else self.opt.timestamp,
        )
        self.opt.expr_dir = expr_dir
        if self.is_train:
            print("------------ Options -------------")
            for k, v in sorted(args.items()):
                print("%s: %s" % (str(k), str(v)))
            print("-------------- End ----------------")

            # save to the disk

            util.mkdir(expr_dir)

            file_name = os.path.join(expr_dir, "opt.txt")
            with open(file_name, "wt") as opt_file:
                opt_file.write("------------ Options -------------\n")
                for k, v in sorted(args.items()):
                    opt_file.write("%s: %s\n" % (str(k), str(v)))
                opt_file.write("-------------- End ----------------\n")
        return self.opt
