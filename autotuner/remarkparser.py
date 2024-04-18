# coding=utf-8
"""
Extended utilities for parsing Remarks
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
from autotuner.optrecord import Remark
from autotuner.optrecord import Loader
import yaml


class AutoTuning(Remark):
    yaml_tag = '!AutoTuning'

    @property
    def color(self):
        return "orange"

    @property
    def key(self):
        key_tuple = super().key + (self.CodeRegionType, self.Args, self.Pass)
        # DebugLoc is optional in autotuner
        if hasattr(self, "DebugLoc"):
            key_tuple += (self.DebugLoc,)
        return key_tuple


def get_remarks(input_file):
    all_remarks = []

    with open(input_file) as input_file_handler:
        docs = yaml.load_all(input_file_handler, Loader=Loader)

        for remark in docs:
            all_remarks.append(remark)

    return all_remarks
