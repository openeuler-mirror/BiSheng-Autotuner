# coding=utf-8
"""
Autotuner's command-line interface.
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
from __future__ import print_function

import argparse
import logging
import os
try:
    from importlib.metadata import metadata, PackageNotFoundError
except ImportError:
    from importlib_metadata import metadata, PackageNotFoundError

import opentuner

import autotuner.utils as utils
from autotuner.resumable.interface import AutoTunerInterface
from autotuner.resumable.interface import StateSerializer
from autotuner.iomanager import argument_parser as io_argument_parser

log = logging.getLogger(__name__)

MAX_PARALLELISM = 4096 # Define maximum number of trials in parallel.


def initialize(data_dir, args, objective, trials):
    state_serializer = StateSerializer(data_dir)
    # Check if the autotuner state exists already at initialization.
    state_serializer.check_state_exists()
    auto_tuner = AutoTunerInterface()
    auto_tuner.initialize(args, data_dir, objective)
    auto_tuner.next_config(trials)

    # Serialize auto_tuner into disk.
    state_serializer.serialize(auto_tuner)


def feedback(data_dir, feedback_numbers, trials):
    state_serializer = StateSerializer(data_dir)
    auto_tuning_state = state_serializer.deserialize()
    auto_tuner = AutoTunerInterface()
    auto_tuner.resume(auto_tuning_state)
    auto_tuner.feedback(feedback_numbers)
    auto_tuner.next_config(trials)
    state_serializer.serialize(auto_tuner)


def dump(data_dir):
    state_serializer = StateSerializer(data_dir)
    auto_tuning_state = state_serializer.deserialize()
    auto_tuner = AutoTunerInterface()
    auto_tuner.resume(auto_tuning_state)
    auto_tuner.dump()


def finalize(data_dir, update_type):
    state_serializer = StateSerializer(data_dir)
    auto_tuning_state = state_serializer.deserialize()
    auto_tuner = AutoTunerInterface()
    auto_tuner.resume(auto_tuning_state)
    auto_tuner.finalize(update_type)


def parse_metadata(project_name):
    """
    Parse keyword metadata created by setuptools and
    construct version message.
    """
    try:
        distribution_metadata_dict = metadata(project_name)
        name = distribution_metadata_dict['Summary']
        version = distribution_metadata_dict['Version']
        git_hash, date = distribution_metadata_dict['Keywords'].split(',')
    except (ValueError, AttributeError, PackageNotFoundError):
        name = "BiSheng Autotuner"
        version = "(dev)"
        git_hash = ""
        date = ""

    version_message = "{name} {version}".format(name=name, version=version)
    if len(git_hash) > 0:
        version_message += " (commit-{hash} {date})"\
                            .format(hash=git_hash, date=date)
    return version_message


def create_parser():
    # Create the top-level parser
    top_parser = argparse.ArgumentParser(prog="llvm-autotune",
                                formatter_class=argparse.RawTextHelpFormatter)

    top_parser.add_argument('-v', '--version', action='version',
                    version=parse_metadata('autotuner'))

    sub_parsers = top_parser.add_subparsers(dest="command")
    sub_parsers.required = True

    # Create parsers for the "minimize/maximize" command
    parent_parsers = opentuner.argparsers()
    parent_parsers.append(io_argument_parser)
    # Suppress help messages from parent argument parsers (opentuner) which
    # users should not be aware of.
    for parser in parent_parsers:
        for argument in parser._actions:
            argument.help = argparse.SUPPRESS
    _suppress_help_messages(parent_parsers)

    min_parser = sub_parsers.add_parser("minimize", parents=parent_parsers,
                                formatter_class=argparse.RawTextHelpFormatter,
                                help="Initialize tuning and generate the "
                                     "initial compiler configuration file, "
                                     "aiming to minimize the metric "
                                     "(e.g. run time)")

    max_parser = sub_parsers.add_parser("maximize", parents=parent_parsers,
                                formatter_class=argparse.RawTextHelpFormatter,
                                help="Initialize tuning and generate the "
                                     "initial compiler configuration file, "
                                     "aiming to maximize the metric "
                                     "(e.g. throughput)")
    for parser in (min_parser, max_parser):
        _add_arg_trials(parser)
        _add_arg_search_space(parser)
        _add_arg_deterministic(parser)
        _add_config_db_arguments(parser)
        _add_code_region_filtering_arguments(parser)
        _add_use_dynamic_values(parser)
        _add_arg_baseline_config(parser)

    # Create the the parser for the "feedback" command
    feedback_parser = sub_parsers.add_parser("feedback",
                                formatter_class=argparse.RawTextHelpFormatter,
                                help="Feed back performance tuning result(s) "
                                     "and generate new test configurations")

    _add_arg_trials(feedback_parser)

    sub_parsers.add_parser("dump",
                           formatter_class=argparse.RawTextHelpFormatter,
                           help="Dump the current best configuration without "
                                "terminating the tuning run")
    feedback_parser.add_argument("values", type=float, nargs='*',
                                 help="Performance tuning result(s)")
    feedback_parser.add_argument("-i", "--feedback-file",
                                 help="Load feedback values from "
                                      "a CSV file; any values "
                                      "specified on command line are "
                                      "overridden by those specified in the "
                                      "file")

    # Create the parser for the "finalize" command.
    finalize_parser = sub_parsers.add_parser("finalize",
                           formatter_class=argparse.RawTextHelpFormatter,
                           help="Finalize tuning and generate the optimal "
                                "compiler configuration")
    finalize_parser.add_argument("--store-optimal-configs",
                                 dest="config_update", action="store_true",
                                 help="specifiy if the optimal configuration "
                                      "will be stored in configs.db upon "
                                      "completion. It will overwrite previous "
                                      "rows on conflict. "
                                      "Default: No update.")

    return top_parser


def main():
    # Create the top-level parser
    top_parser = create_parser()

    # Parse arguments
    args = top_parser.parse_args()
    # Use opentuner's logging format.
    opentuner.init_logging()
    # Get data_dir where tuning state and other tuning related data is saved
    # from the environment variable AUTOTUNE_DATADIR.
    if "AUTOTUNE_DATADIR" in os.environ:
        data_dir = os.environ["AUTOTUNE_DATADIR"]
    else:
        data_dir = "autotune_datadir"
        log.warning(
            "Environment variable AUTOTUNE_DATADIR is not set; "
            "a default directory is used for saving the data: %s", data_dir)
    try:
        if args.command == "minimize" or args.command == "maximize":
            initialize(data_dir, args, args.command, args.trials)
        elif args.command == "feedback":
            if args.feedback_file:
                values = utils.parse_feedback_file(args.feedback_file)
            elif args.values:
                values = args.values
            else:
                raise Exception("No performance feedback provided")
            feedback(data_dir, values, args.trials)
        elif args.command == "dump":
            dump(data_dir)
        elif args.command == "finalize":
            finalize(data_dir, args.config_update)
    except Exception as error:
        log.error(error)
        log.error("Executing command %s failed", args.command)
        exit(1)


def _add_arg_trials(parser):
    def positive_int(value):
        ivalue = int(value)
        if ivalue <= 0:
            raise argparse.ArgumentTypeError(
                "{} is an invalid positive int value".format(ivalue))
        if ivalue > MAX_PARALLELISM:
            raise argparse.ArgumentTypeError(
                "Maximum number of trials is {}".format(MAX_PARALLELISM))
        return ivalue

    parser.add_argument("--trials", type=positive_int, default=1,
                        help="Specify the number of trials to be tested "
                             "in the next iteration")
    return parser


def _add_arg_deterministic(parser):
    def str2bool(value):
        if value.lower() in ['true', '1', 'yes', 't', 'y']:
            return True
        elif value.lower() in ['false', '0', 'no', 'f', 'n']:
            return False
        else:
            raise argparse.ArgumentTypeError(
                "Invalid value: {}".format(value))

    parser.add_argument("--deterministic", type=str2bool, default=False,
                        help="Enable deterministic tuning mode to generate "
                             "reproducible results/output. For testing "
                             "purposes only; off by default. [True/False]")

    parser.add_argument("--seed", default=0x31337,
                        help="Specifying the seed value for Random Number "
                             "Generator. For testing purposes only")

    parser.add_argument("--seed-file", type=str,
                        help="Specify the path of seed file for Random Number "
                             "Generator. This option requires "
                             "'--deterministic=True'.")


def _add_arg_search_space(parser):
    parser.add_argument("--search-space",
                        help="Specify the path of search space file")
    return parser


def _add_config_db_arguments(parser):
    parser.add_argument("--use-hash-matching",
                        dest="use_hash_matching", action="store_true",
                        help="Assign same configuration to the opportunities "
                             "which have same hash value.")

    parser.add_argument("--use-optimal-configs",
                        dest="use_optimal_configs",
                        choices=["none", "reuse", "retune"],
                        default="none",
                        help="Use previously found/stored configurations for "
                             "code regions for current tuning.\n"
                             "Options: {none[Default], reuse, retune}. "
                             "reuse/retune can only be used when "
                             "'use-hash-matching' is enabled.\n"
                             "none: Do not reuse the old configurations.\n"
                             "reuse: Reuse the old optimal configurations "
                             "found and tune code regions which don't have "
                             "optimal configurations stored in database.\n"
                             "retune: Retune all the code regions and use "
                             "the optimal configurations (found in database) "
                             "as starting point for AutoTuner.\n")
    return parser


def _add_code_region_filtering_arguments(parser):
    parser.add_argument('--name-filter', nargs='+', metavar='Name',
                        default=[],
                        help='Generate search space to include only code '
                             'regions named in space-delimited list.')
    parser.add_argument('--func-name-filter', nargs='+', metavar='Name',
                        default=[],
                        help='Generate search space to include only code '
                             'regions having function name in space-delimited '
                             'list.')
    parser.add_argument('--file-name-filter', nargs='+', metavar='Name',
                        default=[],
                        help='Generate search space to include only code '
                             'regions having file name in space-delimited '
                             'list.')
    parser.add_argument('--pass-filter', nargs='+', metavar='Name',
                        default=[],
                        help='Generate search space to include only code '
                             'regions of a specific pass.')
    parser.add_argument('--type-filter', nargs='+', metavar='Name',
                        default=[],
                        help='Generate search space to include only code '
                             'regions having type in space-delimited list.\n'
                             'Options: [loop, callsite, machine_basic_block, '
                                        'other, llvm-param, program-param',
                        choices=['loop', 'callsite', 'machine_basic_block',
                                 'other', 'llvm-param', 'program-param'])
    return parser

def _add_use_dynamic_values(parser):
    parser.add_argument('--use-dynamic-values', action='store_true',
                        help='Turn on dynamic values suggested by the compiler'
                             'Default: turned off')


def _add_arg_baseline_config(parser):
    parser.add_argument("-b", '--use-baseline-config', action='store_true',
                        help='Start the search from the baseline configuration'
                             ' instead of a random point in the search space'
                             ' (default).')


def _suppress_help_messages(parsers):
    for parser in parsers:
        for argument in parser._actions:
            argument.help = argparse.SUPPRESS


if __name__ == "__main__":
    main()
