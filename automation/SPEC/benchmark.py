#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
import argparse
import configparser
import os
import shlex
import subprocess
import sys
from shutil import which

import accumulate
from reader import find_largest_num
from reader import get_infix
from reader import get_suite
from reader import log
from reader import parse_baseline
from reader import parse_autotuner

RUNCPU_TEMPLATE = "runcpu {0} --tune=base --rebuild --config=llvm.cfg " \
                  "--noreportable -S LLVM_DIR={1} --size={2} "
RUNCPU_TEMPLATE += ""  # Add your extra configuration here

AUTOTUNER_TEMPLATE = "auto-tuner auto_run {0} -tr spec_tuner " \
                     "--plugin-dir {1} --results-log-details " \
                     "module_detail.log  --stage-order loop " \
                     "--stop-after {2} -o {3} "
AUTOTUNER_TEMPLATE += ""  # Add your extra configuration here

START_CSV_NUM = None
END_CSV_NUM = None


def execute_command(command: list, fake: bool):
    """
    Execute a subprocess. Not run if fake.
    """
    log("EXECUTE COMMAND:", *command)
    if not fake:
        subprocess.run(command)


def expand_path(path: str):
    """
    Support relative path for command line args
    """
    path = os.path.expanduser(path)
    path = os.path.expandvars(path)
    # resolve any symbolic links in the path,
    # and then return the absolute path
    path = os.path.realpath(path)
    return path


def args_check(args):
    """
    Check whether the args are valid or not. Exit if necessary.
    """
    # Check runcpu and autotuner commands exists
    for item in ("runcpu", "auto-tuner"):
        if not which(item):
            log("{} command not found, exit".format(item))
            sys.exit(1)

    # Get llvm_dir
    config = configparser.ConfigParser()
    config.read(args.config_spec)
    args.llvm_dir = config["Compiling Setting"]["LLVM_DIR"]

    # Standardize path
    llvm_dir = expand_path(args.llvm_dir)
    result_dir = expand_path(args.result_dir)
    config_spec = expand_path(args.config_spec)
    plugin_dir = expand_path(args.plugin_dir)
    output = expand_path(args.output)

    # Check directory exist
    for path in (llvm_dir, result_dir,
                 config_spec, plugin_dir):
        if not os.path.exists(path):
            log("No such file or directory")
            sys.exit(1)

    # Check every benchmark has a stop time
    if len(args.benchmarks) != len(args.stop_after):
        log("Invalid number of argument for --stop-after. " /
            "Need to match with num of benchmarks")
        sys.exit(1)

    # Check benchmarks are vaild
    # get_suite will exit if mark is not a valid benchmark number
    [get_suite(mark) for mark in args.benchmarks]

    # Make sure dir path is formatted
    if result_dir[-1] != '/':
        result_dir += '/'
    if output[-1] != '/':
        output += '/'

    # Clean if necessary
    if args.clean:
        for filename in os.listdir(result_dir):
            try:
                if not args.fake:
                    os.remove(result_dir + filename)
                log("remove {}".format(filename), extra_line=False)
            except IsADirectoryError as e:
                log("can not remove directory {}, please remove manually"
                    .format(e.filename))

    # Check output directory
    if not os.path.exists(output):
        log("No existing output directory, creating a new directory")
        os.makedirs(output)
        # create four accumulate files
        for filename in ("intspeed.csv", "intrate.csv",
                         "fpspeed.csv", "fprate.csv"):
            accumulate.init_accumulate(output, filename)
    else:
        for filename in ("intspeed.csv", "intrate.csv",
                         "fpspeed.csv", "fprate.csv"):
            file_path = os.path.realpath(output + filename)
            if not os.path.exists(file_path):
                accumulate.init_accumulate(output, filename)


def get_args():
    parser = argparse.ArgumentParser(
        description="Automation script for auto-tuner SPEC benchmarks.")

    parser.add_argument("benchmarks", nargs='+', help="The benchmarks to run.")
    parser.add_argument("-s", "--stop-after", nargs='+', required=True,
                        help="Stop autotuner benchmarks after given " \
                        "seconds. Need to support multiple values if " \
                        "multiple benchmarks. Required.")
    parser.add_argument("-r", "--result-dir", default="$SPEC/result/",
                        help="Directory of SPEC produced result csv files " \
                        "(default $SPEC/result/).")
    parser.add_argument("-c", "--config-spec", default="./spec_automation.ini",
                        help="Location of spec_sample.ini file " \
                        "(default ./spec_automation.ini).")
    parser.add_argument("-p", "--plugin-dir", default="../../autotuner/plugin",
                        help="Directory of Autotuner plugin " \
                        "(default ../../autotuner/plugin/).")
    parser.add_argument("-o", "--output", default="./automation-output/",
                        help="Directory where results are accumulated " \
                        "(default: ./automation-output/).")
    parser.add_argument("-i", "--size", default="ref", choices=["ref",
                                                                "train",
                                                                "test"],
                        help="Size of SPEC input data to run (default: ref).")
    parser.add_argument("--fake", action="store_true",
                        help="List, but do not execute, the commands " \
                        "needed to build or run the benchmarks.")
    parser.add_argument("--clean", action="store_true",
                        help="Before running benchmarks, remove all " \
                        "files from a given (cpu2017/result) folder.")

    args = parser.parse_args()
    return args


def run_baseline(args, i: int) -> float:
    """
    Run SPEC baseline with given benchmark in args.benchmark[i]
    Return the time it takes for baseline to run
    """
    global START_CSV_NUM
    mark = args.benchmarks[i]
    # Find largest
    flag = find_largest_num(args.result_dir)
    START_CSV_NUM = flag + 1 if flag else 1

    # Run baseline
    baseline_cmd = shlex.split(
        RUNCPU_TEMPLATE.format(mark, args.llvm_dir, args.size))
    execute_command(baseline_cmd, args.fake)
    # TODO check return code

    log("BASELINE RUN FINISHED")

    baseline_runtime = "FAKE DATA"
    if not args.fake:
        baseline_runtime = parse_baseline(
            get_infix(mark, args.size), mark, START_CSV_NUM, args.result_dir)

    return baseline_runtime


def run_autotuner(args, i: int) -> float:
    """
    Run Autotuner SPEC with given benchmark in args.benchmark[i]
    Return the best time autotuner can produce
    """
    global START_CSV_NUM, END_CSV_NUM

    # For dynamically setting SPEC input size and benchmark in spec_sample.ini
    mark = args.benchmarks[i]
    stop_time = args.stop_after[i]
    os.environ["AUTOMATION_BENCHMARK_NAME"] = mark
    log('ADD ENV "AUTOMATION_BENCHMARK_NAME" = {}'.format(mark))
    os.environ["AUTOMATION_SPEC_SIZE"] = args.size
    log('ADD ENV "AUTOMATION_SPEC_SIZE"')

    # Run autotuner SPEC
    autotuner_cmd = shlex.split(AUTOTUNER_TEMPLATE.format(
        args.config_spec, args.plugin_dir, stop_time, mark))
    execute_command(autotuner_cmd, args.fake)

    # Update END_CSV_NUM
    flag = find_largest_num(args.result_dir)
    END_CSV_NUM = flag if flag else 1
    # Parse autotuner result
    autotuner_runtime = "FAKE DATA"
    if not args.fake:
        # Parse from
        # START_CSV_NUM + 2(include one SPEC result for build) TO END_CSV_NUM
        autotuner_runtime = parse_autotuner(get_infix(
            mark, args.size), mark, START_CSV_NUM + 2,
            END_CSV_NUM, args.result_dir)
    return autotuner_runtime


def main():
    global START_CSV_NUM, END_CSV_NUM

    # This script was designed to run inside a Docker container, but may
    # work just fine outside.
    path = os.path.realpath("/.dockerenv")
    if not os.path.exists(path):
        log("Warning: running outside a Docker container.")

    args = get_args()
    args_check(args)

    if args.fake:
        START_CSV_NUM = END_CSV_NUM = 0

    lst_baseline_runtime = []
    lst_autotuner_runtime = []
    lst_iterations = []

    for i in range(len(args.benchmarks)):
        baseline_runtime = run_baseline(args, i)
        log("BASELINE RUNTIME: {}".format(baseline_runtime))

        autotuner_runtime = run_autotuner(args, i)

        mark = args.benchmarks[i]
        log("BENCHMARK: {}".format(mark), extra_line=False)
        log("BASELINE RUNTIME: {}".format(baseline_runtime), extra_line=False)
        log("AUTOTUNER BEST RUNTIME: {}".format(
            autotuner_runtime), extra_line=False)
        iteration = END_CSV_NUM - START_CSV_NUM - 1
        log("ITERATIONS: {}".format(iteration))

        lst_baseline_runtime.append(baseline_runtime)
        lst_autotuner_runtime.append(autotuner_runtime)
        lst_iterations.append(iteration)

        # update csv
        if not args.fake:
            accumulate.update(args.output + get_suite(mark), mark,
                              baseline_runtime, autotuner_runtime, iteration)

    # Do a final log
    log("SUMMARY:")
    for i in range(len(args.benchmarks)):
        b_time = lst_baseline_runtime[i]
        a_time = lst_autotuner_runtime[i]
        i_time = lst_iterations[i]
        log("BENCHMARK: {}".format(args.benchmarks[i]), extra_line=False)
        log("BASELINE RUNTIME: {}".format(b_time), extra_line=False)
        log("AUTOTUNER BEST RUNTIME: {}".format(a_time), extra_line=False)
        log("ITERATIONS: {}".format(i_time))


if __name__ == "__main__":
    main()
