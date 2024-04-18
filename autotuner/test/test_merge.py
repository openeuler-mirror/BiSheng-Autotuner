#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for merge command
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
import os
import unittest
import unittest.mock as mock
import yaml
from autotuner.main import merge_main
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


class TestAutotunerMerge(unittest.TestCase):
    """
    Test the 'merge' subcommand in autotuner
    """

    def setUp(self):
        self.args = mock.MagicMock()
        self.args.command = "merge"
        self.args.parse_format = "yaml"

    def compare_yaml_content(self, expected_yaml_path, actual_yaml_path):
        """
        Compare two yaml files by their contents using pyyaml
        """
        try:
            with open(expected_yaml_path) as expected_stream, open(
                    actual_yaml_path) as actual_stream:
                actual_generator = yaml.load_all(actual_stream, Loader=Loader)
                for expected_remark in yaml.load_all(expected_stream,
                                                     Loader=Loader):
                    actual_remark = next(actual_generator)
                    self.assertEqual(expected_remark, actual_remark,
                                     "Parsed result yaml different "
                                     "from expected")
                # expected has finished, check whether actual finished too
                # if the actual_generator still has content, then fail
                self.assertRaises(StopIteration, next, actual_generator)
        finally:
            os.unlink(actual_yaml_path)

    def test_merge_main(self):
        curr_dir = os.path.dirname(__file__)
        self.args.input_file = [os.path.join(curr_dir,
                        "Inputs/merge/llvm_input_core_list_join.c.yaml"),
                                os.path.join(curr_dir,
                        "Inputs/merge/llvm_input_core_main.c.yaml")]
        self.args.output = "actual_merge_result.yaml"

        with self.assertRaises(SystemExit) as context:
            merge_main(self.args)
        self.assertEqual(context.exception.code, 0)

        # check file created
        self.assertTrue(os.path.isfile("actual_merge_result.yaml"))
        # check divide output content
        self.compare_yaml_content(os.path.join(
            curr_dir, "Outputs/merge/llvm_input.yaml"),
            "actual_merge_result.yaml")


if __name__ == "__main__":
    unittest.main(buffer=True)
