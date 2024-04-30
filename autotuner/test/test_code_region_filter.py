#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for code region filtering in AutoTuner.
Copyright (C) 2017-2022, Huawei Technologies Co., Ltd. All rights reserved.
"""
import os
import shutil
import unittest
import tempfile
import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from autotuner.resumable.main import create_parser
from autotuner.resumable.main import initialize


class TestCodeRegionFilter(unittest.TestCase):
    """
    This class tests the code region filtering options. We can filter the code
    regions by type, name, file, and function name.
    """

    def setUp(self):
        # Setting environment before running each test.
        self.data_dir = tempfile.TemporaryDirectory()
        os.environ['AUTOTUNE_DATADIR'] = self.data_dir.name
        self.input_dir = os.path.join(os.path.dirname(__file__),
                                           "Inputs/filter_opp/")
        shutil.copytree(self.input_dir, self.data_dir.name + '/opp/')
        self.parser = create_parser()


    def verify_yaml_content(self, yaml_path, expected_code_regions):
        """
        Counting number of generated code regions in yaml file and comparing it
        with the expected number of code regions.
        """
        code_regions = 0
        with open(yaml_path) as stream:
            for _ in yaml.load_all(stream, Loader=Loader):
                code_regions += 1

        self.assertEqual(code_regions, expected_code_regions)


    def test_type_filter(self):
        # Filtering code regions by type.
        args = self.parser.parse_args(['minimize',
                                       '--type-filter', 'loop'])

        initialize(self.data_dir.name, args, args.command, args.trials)
        self.verify_yaml_content(self.data_dir.name + "/config.yaml", 11)

        self.data_dir.cleanup()


    def test_func_name_filter(self):
        # Filtering code regions by containing function name.
        args = self.parser.parse_args(['minimize',
                                        '--func-name-filter', 'pat_insert'])

        initialize(self.data_dir.name, args, args.command, args.trials)
        self.verify_yaml_content(self.data_dir.name + "/config.yaml", 15)

        self.data_dir.cleanup()


    def test_code_region_name_filter(self):
        # Filtering code regions by their names.
        args = self.parser.parse_args(['minimize',
                                    '--name-filter', 'for.body', 'land.rhs'])

        initialize(self.data_dir.name, args, args.command, args.trials)
        self.verify_yaml_content(self.data_dir.name + "/config.yaml", 3)

        self.data_dir.cleanup()


    def test_file_name_filter(self):
        # Filtering code regions by file name.
        args = self.parser.parse_args(['minimize',
                                    '--file-name-filter', 'patricia_test.c'])

        initialize(self.data_dir.name, args, args.command, args.trials)
        self.verify_yaml_content(self.data_dir.name + "/config.yaml", 2)

        self.data_dir.cleanup()


    def test_type_and_file_name_filter(self):
        # Filtering code regions by type and file name.
        args = self.parser.parse_args(['minimize',
                                    '--file-name-filter', 'patricia.c',
                                    '--type-filter', 'callsite'])

        initialize(self.data_dir.name, args, args.command, args.trials)
        self.verify_yaml_content(self.data_dir.name + "/config.yaml", 16)

        self.data_dir.cleanup()


    def test_pass_filter(self):
        # Filtering code regions by optimization pass.
        args = self.parser.parse_args(['minimize', '--pass-filter',
                                       'loop-unroll'])

        initialize(self.data_dir.name, args, args.command, args.trials)
        self.verify_yaml_content(self.data_dir.name + "/config.yaml", 11)

        self.data_dir.cleanup()


if __name__ == "__main__":
    unittest.main(buffer=True)
