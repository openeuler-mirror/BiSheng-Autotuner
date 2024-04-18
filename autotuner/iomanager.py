# coding=utf-8
"""
Abstract base class for YAMLManager and XMLManager
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
import argparse
import abc

argument_parser = argparse.ArgumentParser(add_help=False)
argument_parser.add_argument('--parse-format', nargs='?', choices=[
    'xml', 'yaml'], default='yaml',
    help='choose the format of LLVM auto-tuning-input/opp,'
                            '(default: yaml)')


class EmptySearchSpaceError(Exception):
    pass


class IOManager(object):

    @abc.abstractmethod
    def build_llvm_input(self, configuration_data, task_map, output_file,
                         fixed_llvm_input=None, config_db=None,
                         use_hash_matching=False):
        pass

    @abc.abstractmethod
    def generate_baseline_llvm_input(self, output_file, config_db=None):
        pass

    @abc.abstractmethod
    def parse_search_space(self, search_space, use_dynamic_values=False,
                           use_baseline_config = False, filepath = None):
        pass

    @abc.abstractmethod
    def parse_llvm_inputs(self, input_files):
        pass

    @abc.abstractmethod
    def divide_llvm_input(self, input_file):
        pass

    @abc.abstractmethod
    def generate_search_space_file(self, files, output_file, config_file,
                                   name_filter=None, func_name_filter=None,
                                   file_name_filter=None, type_filter=None,
                                   pass_filter=None, config_db=None,
                                   use_hash_matching=False,
                                   use_prev_configs=False, inject_seed=False):
        pass

    @abc.abstractmethod
    def generate_search_space(self, files, config_file, file_name_filter,
                              func_name_filter, name_filter, type_filter,
                              pass_filter, config_db=None,
                              use_hash_matching=False, use_prev_configs=False,
                              inject_seed=False):
        pass

    @abc.abstractmethod
    def output_to_file(self, output_file, content):
        pass

    @abc.abstractmethod
    def get_file_extension(self):
        pass

    @abc.abstractmethod
    def create_dummy_llvm_input(self, output_file):
        """
        Create a dummy llvm config input file.
        """
        pass
