# coding=utf-8
"""
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
import os
import re

from opentuner import Result
from opentuner.search.objective import MinimizeCycle
from autotuner.tuners.tunerbase import CustomTunerBase


class Tuner(CustomTunerBase):

    def __init__(self, *pargs, **kwargs):

        super(Tuner, self).__init__(*pargs, **kwargs)
        result_path = os.path.join(self.compile_dir,
                                   "llt/model/st/data/AICore_Conv3_x/")
        result_path = os.path.realpath(result_path)
        if not os.path.exists(result_path):
            os.makedirs(result_path)

    # The run method runs opentuner under the given configuration
    # and returns the calculated performance under this configuration
    def run(self, desired_result, desired_input, limit):
        """
        Compile and run a given configuration then
        return performance
        """
        cycles = float('inf')
        cfg = desired_result.configuration.data

        # run the simulator
        run_result = self.call_program(self.run_cmd,
                                       cwd=self.run_dir, limit=1500)

        # check if the source program is compiled and run successful
        if run_result['returncode'] == 0:
            result_file_path = os.path.join(self.run_dir,
                                "llt/model/st/data/AICore_Conv3_x/instr.dump")
            with open(result_file_path) as result_file:
                last_line = result_file.readlines()[-2].strip()
                match = re.search(r"\[([0-9_]+)\]", last_line)
                cycles = int(match.groups()[0])
        else:
            print('errors detected')
            self._print_errors(self.run_cmd, run_result)
            if not os.path.isdir('errors_log'):
                os.mkdir('errors_log')
            self.iomanager.build_llvm_input(
                cfg, self.task_map, "errors_log/errors_config_" +
                str(desired_result.configuration.id) + ".xml")

        # get the stdout of the benchmark programs
        # Parse the stdout to get the result list
        return Result(cycle=cycles, time=run_result['time'])

    def objective(self):
        """
        Override the default object MinimizeTime
        """
        return MinimizeCycle()
