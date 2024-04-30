# coding=utf-8
"""
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
import os
import re
from opentuner import Result
from opentuner.search.objective import MinimizeCycle
from autotuner.tuners.tunerbase import CustomTunerBase
from autotuner.utils import create_secure_fd


class Tuner(CustomTunerBase):

    # The run method runs opentuner under the given configuration
    # and returns the calculated performance under this configuration
    def run(self, desired_result, desired_input, limit):
        """
         Compile and run a given configuration then
         return performance
         """
        cycles = float('inf')

        # create a command for running a executable
        run_result = self.call_program(
            self.run_cmd, cwd=self.run_dir, limit=10000)
        # check if the source program is compiled and run successful
        if run_result['returncode'] == 0:
            std = run_result['stdout']
            if "Success:" in std:
                find_path = "format: Text"
                find_name = "Success:"
                all_line = std.strip().splitlines()
                path = None
                benchmark_name = None
                for line in all_line:
                    if re.search(find_path, line):
                        words = line.split()
                        path = words[-1]
                    if re.search(find_name, line):
                        words = line.split()
                        benchmark_name = words[-1]
                        benchmark_name = benchmark_name[2:]

                if(not path.endswith('.txt')):
                    print("Error: Extract path fails")
                    return Result(cycle=cycles, time=run_result['time'])
                if(benchmark_name is None):
                    print("Error: Extract benchmark name fails")
                    return Result(cycle=cycles, time=run_result['time'])

                with open(path, "r") as result_file:
                    result = result_file.readlines()
                    for txt_line in result:
                        if re.search(benchmark_name, txt_line):
                            cycles = txt_line.split()[2]
                            if (cycles != '(base)'):
                                return Result(cycle=cycles, time=cycles)

                print("Error: finding benchmark name in the txt file fails")
                return Result(cycle=cycles, time=run_result['time'])
            else:
                print("Not success")
                if not os.path.isdir('errors_log'):
                    os.mkdir('errors_log')

                fd = create_secure_fd("errors_log/errors_" +
                          str(desired_result.configuration.id) + ".log")
                with os.fdopen(fd, 'w') as error_log_file:
                    error_log_file.write(std)
                print('custom errors detected')
        else:
            print("Returncode non-zero")
            self._print_errors(self.run_cmd, run_result)

        return Result(cycle=cycles, time=run_result['time'])

    def objective(self):
        """
        Override the default object MinimizeTime
        """
        return MinimizeCycle()
