# coding=utf-8
"""
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
import abc
import argparse
import os
import re
from datetime import datetime

from opentuner import ConfigurationManipulator
from opentuner import MeasurementInterface
from opentuner import Result
from autotuner.iomanagerutils import create_io_manager

argument_parser = argparse.ArgumentParser(add_help=False)
argument_parser.add_argument('--time-after-convergence', '-tac', type=float,
                             metavar='TIME',
                             help='stop tuning if no new best results after '
                                  'given seconds')
argument_parser.add_argument('-o', '--output', metavar='DIR',
                             help='write optimal yaml config into the given '
                                  'directory')

STAGES = ['module', 'function', 'loop', 'machine_basic_block']


class TunerBase(MeasurementInterface):
    """
    Abstract base class for tuning-enabled LLVM related auto-tuning
    """

    def __init__(self, args, compile_dir, llvm_config_file, search_space,
                 compile_cmd, fixed_llvm_config_files=None,
                 enable_final_compile=False, stage=None, config_db=None,
                 *pargs, **kwargs):
        super(TunerBase, self).__init__(args, *pargs,
                                        **kwargs)
        self.iomanager = create_io_manager(args.parse_format)
        self.compile_dir = compile_dir
        self.llvm_input_file = llvm_config_file
        self.compile_cmd = compile_cmd
        self.task_map = self.iomanager.parse_search_space(search_space)
        self.config_db = config_db
        self.use_hash_matching = args.use_hash_matching

        if fixed_llvm_config_files:
            self.fixed_llvm_config_tree = self.iomanager.parse_llvm_inputs(
                fixed_llvm_config_files)
        else:
            self.fixed_llvm_config_tree = None

        self.enable_final_compile = enable_final_compile

        # for extra_convergence_criteria
        if args.time_after_convergence:
            self.last_best_result_time = datetime.now()
        if args.output:
            self.output_dir = args.output
        else:
            self.output_dir = ""
        if stage and not stage in STAGES:
            # if a stage is specified, it must be one of machine_basic_block,
            # function, loop, or module
            # FIXME use Enum class instead after upgrading to python3.4
            raise Exception("Illegal stage: " + stage)
        self.stage = stage

    def manipulator(self):
        """
        Overide manipulator from MeasurementInterface.
        """
        manipulator = ConfigurationManipulator()
        for _, task in self.task_map.items():
            for param in task.param_list:
                manipulator.add_parameter(param)
        return manipulator

    def compile(self, config_data=None, compile_id=None):
        # run the compile command
        compile_result = self.call_program(self.compile_cmd,
                                           cwd=self.compile_dir, limit=1500)
        return compile_result

    def compile_and_run(self, desired_result, desired_input, limit):
        """
        Override compile_and_run from MeasurementInterface.
        """
        cfg = desired_result.configuration.data

        self.iomanager.build_llvm_input(
            cfg, self.task_map, self.llvm_input_file,
            self.fixed_llvm_config_tree,
            self.config_db, self.use_hash_matching)

        # compiler the program
        compile_result = self.compile()
        # if compiling failed
        if compile_result['timeout']:
            print("compiling timeoout")
            return Result(state='TIMEOUT', time=float('inf'))
        elif compile_result['returncode'] != 0:
            print("compiling error, test failed")
            print(compile_result["stderr"])
        else:
            return self.run(desired_result, desired_input, limit)

        return Result(state='ERROR', time=float('inf'), cycle=float('inf'),
                      rate=-float('inf'))

    def extra_convergence_criteria(self, result_list):
        """
        The extra convergence criteria which returns True if the
        time elapsed since last best result found exceeds what user specify via
        command line
        """
        if self.args.time_after_convergence:
            # check if any new best results found
            is_any_new_best = any([ele.was_new_best for ele
                                   in result_list]) if result_list else False

            # if there is a new best results found,
            # reset last_best_result_time to now
            if is_any_new_best:
                self.last_best_result_time = datetime.now()
            # otherwise calculate time elapsed since last best result found
            else:
                elapsed = (datetime.now() - self.last_best_result_time).seconds
                if elapsed > self.args.time_after_convergence:
                    print("time elapsed since last best result found: " +
                          str(elapsed))
                    return True

        return False

    # Saves the optimal result of running opentunner
    def save_final_config(self, configuration):
        """Called at the end of tuning"""
        print("Tuning run is ending...")
        if self.enable_final_compile:
            print("Performing final compilation with opt config...")
            self.iomanager.build_llvm_input(configuration.data, self.task_map,
                                            self.llvm_input_file,
                                            self.fixed_llvm_config_tree,
                                            self.config_db,
                                            self.use_hash_matching)
            compile_result = self.compile()
            if compile_result['returncode'] != 0:
                print("Compiling error")
                print(compile_result["stderr"])
            else:
                print("Final compilation succeeded")

        output_name = self.stage if self.stage else "opt_config"
        output_path = os.path.join(self.output_dir, output_name)

        if self.args.config_update_type and self.config_db:
            self.iomanager.update_config_db(
                configuration.data, self.task_map,
                config_db=self.config_db,
                use_hash_matching=self.use_hash_matching)
            print("configs.db has been updated with optimal configurations.")

        self.iomanager.build_llvm_input(
            configuration.data, self.task_map, output_path +
            self.iomanager.get_file_extension(), self.fixed_llvm_config_tree,
            self.config_db, self.use_hash_matching)
        print("Optimal configuration for llvm/clang has been saved to " +
              output_path + self.iomanager.get_file_extension())
        self.manipulator().save_to_file(configuration.data,
                                        output_path + ".json")
        print("Optimal json configuration for opentuner has been saved to " +
              output_path + ".json")
        print("You can use the json file with --seed-configuration "
              "for next tuning run")

    def _print_errors(self, cmd, run_result):
        print('running command failed, the error was: ')
        print(run_result['stderr'])
        print('the cmd was: ')
        print(cmd + '\n')


class CustomTunerBase(TunerBase):
    """
    Abstract base class for non-coddess based tuner
    """

    def __init__(self, args, compile_dir, llvm_config_file, search_space,
                 compile_cmd, run_dir, run_cmd, *pargs, **kwargs):
        super(CustomTunerBase, self).__init__(
            args, compile_dir, llvm_config_file, search_space,
            compile_cmd, *pargs, **kwargs)
        self.run_dir = run_dir
        self.run_cmd = run_cmd

    @abc.abstractmethod
    def run(self, desired_result, desired_input, limit):
        return


"""
utils
"""


def get_available_tuners(tuner_dir):
    tuners = _look_up_tuners_by_dir(tuner_dir) if tuner_dir else ()
    default_tuners = _look_up_tuners_by_dir(__file__)
    return tuners + default_tuners


def _look_up_tuners_by_dir(tuner_dir):
    tuners = ()
    for exist_file in sorted(os.listdir(os.path.dirname(tuner_dir))):
        match = re.match(r'^(.*)[.]py(c?)$', exist_file)
        if match:
            module = match.group(1)
            if module[-6:].lower() == '_tuner':
                tuners += (module,)
    return tuners
