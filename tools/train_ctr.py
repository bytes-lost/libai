# coding=utf-8
# Copyright 2021 The OneFlow Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import random
import sys

import numpy as np
import oneflow as flow

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from libai.config import LazyConfig, default_argument_parser, try_get_key
from libai.engine import CTRTrainer, ctr_setup
from libai.utils.checkpoint import Checkpointer

logger = logging.getLogger("libai." + __name__)


def main(args):
    cfg = LazyConfig.load(args.config_file)
    cfg = LazyConfig.apply_overrides(cfg, args.opts)
    ctr_setup(cfg, args)

    seed_for_rank = cfg.train.seed + flow.env.get_rank()
    flow.manual_seed(seed_for_rank)
    flow.cuda.manual_seed(seed_for_rank)
    np.random.seed(seed_for_rank)
    random.seed(seed_for_rank)

    if args.fast_dev_run:
        cfg.train.train_epoch = 0
        cfg.train.train_iter = 20
        cfg.train.evaluation.eval_period = 10
        cfg.train.log_period = 1

    if args.eval_only:
        model = CTRTrainer.build_model(cfg)
        Checkpointer(model, save_dir=cfg.train.output_dir).resume_or_load(
            cfg.train.load_weight, resume=args.resume
        )
        if try_get_key(cfg, "train.graph.enabled", default=False):
            model = CTRTrainer.build_graph(cfg, model, is_train=False)
        test_loader = CTRTrainer.build_test_loader(cfg, tokenizer)
        if len(test_loader) == 0:
            logger.info("No dataset in dataloader.test, please set dataset for dataloader.test")
        _ = CTRTrainer.test(cfg, test_loader, model)
        return

    trainer = CTRTrainer(cfg)
    return trainer.train()


if __name__ == "__main__":
    args = default_argument_parser().parse_args()
    main(args)
