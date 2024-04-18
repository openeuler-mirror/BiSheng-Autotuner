# coding=utf-8
"""
A dummy tuner for test purpose
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
from autotuner.tuners.tunerbase import CustomTunerBase


class Tuner(CustomTunerBase):
    """
    This class is a placeholder for unittest with autotuner's --tuner flag
    """

    def run(self, desired_result, desired_input, limit):
        raise NotImplementedError
