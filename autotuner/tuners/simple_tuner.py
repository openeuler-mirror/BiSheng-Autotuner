# coding=utf-8
"""
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
# import module from parent dir
import os

from opentuner import Result
from opentuner.search.objective import MinimizeCycle
from autotuner.tuners.tunerbase import CustomTunerBase


class SimpleTuner(CustomTunerBase):

    # The run method runs opentuner under the given configuration
    # and returns the calculated performance under this configuration
    def run(self, desired_result, desired_input, limit):
        """
         Compile and run a given configuration then
         return performance
         """
        time = float('inf')

        # create a command for running a executable
        run_result = self.call_program(self.run_cmd,
                                       cwd=self.run_dir, limit=120)

        # check if the source program is compiled and run successful
        if run_result['returncode'] == 0:
            time = run_result['time']
        else:
            self._print_errors(self.run_cmd, run_result)

        return Result(time=time)
