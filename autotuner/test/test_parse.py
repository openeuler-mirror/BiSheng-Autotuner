#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for parse commands
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
import os
import unittest
import unittest.mock as mock
import yaml
from autotuner.main import parse_main
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


class TestAutotunerParse(unittest.TestCase):
    """
    Test the 'parse' subcommand in autotuner
    """

    def setUp(self):
        self.args = mock.MagicMock()
        self.args.command = "parse"

        self.args.opp_file = [os.path.join(os.path.dirname(__file__),
                                           "Inputs/opp/core_list_join.c.yaml"),
                              os.path.join(os.path.dirname(__file__),
                                           "Inputs/opp/core_main.c.yaml")]
        self.args.output = "actual_search_space.yaml"
        self.args.name_filter = []
        self.args.func_name_filter = []
        self.args.file_name_filter = []
        self.args.hot_func_file = []
        self.args.hot_func_number = 10
        self.args.search_config_file = os.path.join(
            os.path.dirname(__file__),
            "Inputs/parse/test_search_space_config.yaml")

    def compare_yaml_content(self, expected_yaml_path, actual_yaml_path):
        """
        Compare two yaml files by their contents using pyyaml
        """
        try:
            with open(expected_yaml_path) as expected_stream, open(
                    actual_yaml_path) as actual_stream:
                actual_generator = yaml.load_all(actual_stream,
                                                 Loader=Loader)
                for expected_dict in yaml.load_all(expected_stream,
                                                   Loader=Loader):
                    actual_dict = next(actual_generator)
                    self.assertDictEqual(
                        expected_dict, actual_dict, "Parsed result yaml "
                        "different from expected")
                # expected has finished, check whether actual finished too
                # if the actual_generator still has content, then fail
                self.assertRaises(StopIteration, next, actual_generator)
        finally:
            os.unlink(actual_yaml_path)

    def test_parse_main(self):
        self.args.type_filter = []

        with self.assertRaises(SystemExit) as context:
            parse_main(self.args)
        self.assertEqual(context.exception.code, 0)

        expected_ss_path = os.path.join(os.path.dirname(
            __file__), "Outputs/parse/search_space.yaml")
        self.compare_yaml_content(expected_ss_path, "actual_search_space.yaml")

    def test_parse_main_loop_only(self):
        self.args.type_filter = ["loop"]

        with self.assertRaises(SystemExit) as context:
            parse_main(self.args)
        self.assertEqual(context.exception.code, 0)

        expected_ss_path = os.path.join(os.path.dirname(
            __file__), "Outputs/parse/search_space_loop_only.yaml")
        self.compare_yaml_content(expected_ss_path, "actual_search_space.yaml")

    def test_parse_main_function_only(self):
        self.args.type_filter = ["function"]

        with self.assertRaises(SystemExit) as context:
            parse_main(self.args)
        self.assertEqual(context.exception.code, 0)

        expected_ss_path = os.path.join(os.path.dirname(
            __file__), "Outputs/parse/search_space_function_only.yaml")
        self.compare_yaml_content(expected_ss_path, "actual_search_space.yaml")

    def test_parse_main_module_only(self):
        self.args.type_filter = ["module"]

        with self.assertRaises(SystemExit) as context:
            parse_main(self.args)
        self.assertEqual(context.exception.code, 0)

        expected_ss_path = os.path.join(os.path.dirname(
            __file__), "Outputs/parse/search_space_module_only.yaml")
        self.compare_yaml_content(expected_ss_path, "actual_search_space.yaml")

    def test_parse_main_mbb_only(self):
        self.args.type_filter = ["machine_basic_block"]

        with self.assertRaises(SystemExit) as context:
            parse_main(self.args)
        self.assertEqual(context.exception.code, 0)

        expected_ss_path = os.path.join(os.path.dirname(
            __file__), "Outputs/parse/search_space_mbb_only.yaml")
        self.compare_yaml_content(expected_ss_path, "actual_search_space.yaml")

    def test_parse_main_name_filter(self):
        self.args.type_filter = []
        self.args.name_filter = ["while.body", "land.rhs"]

        with self.assertRaises(SystemExit) as context:
            parse_main(self.args)
        self.assertEqual(context.exception.code, 0)

        expected_ss_path = os.path.join(os.path.dirname(
            __file__), "Outputs/parse/search_space_name_filter.yaml")
        self.compare_yaml_content(expected_ss_path, "actual_search_space.yaml")

    def test_parse_main_func_filter(self):
        self.args.type_filter = []
        self.args.func_name_filter = ["core_list_find"]

        with self.assertRaises(SystemExit) as context:
            parse_main(self.args)
        self.assertEqual(context.exception.code, 0)

        expected_ss_path = os.path.join(os.path.dirname(
            __file__), "Outputs/parse/search_space_func_filter.yaml")
        self.compare_yaml_content(expected_ss_path, "actual_search_space.yaml")

    def test_parse_main_file_filter(self):
        self.args.type_filter = []
        self.args.file_name_filter = ["core_list_join.c"]

        with self.assertRaises(SystemExit) as context:
            parse_main(self.args)
        self.assertEqual(context.exception.code, 0)

        expected_ss_path = os.path.join(os.path.dirname(
            __file__), "Outputs/parse/search_space_file_filter.yaml")
        self.compare_yaml_content(expected_ss_path, "actual_search_space.yaml")

    def test_parse_main_loop_only_with_file_filter(self):
        self.args.type_filter = ["loop"]
        self.args.file_name_filter = ["core_main.c"]

        with self.assertRaises(SystemExit) as context:
            parse_main(self.args)
        self.assertEqual(context.exception.code, 0)

        expected_ss_path = os.path.join(os.path.dirname(__file__),
                                        "Outputs/parse/search_space_"
                                        "loop_only_with_file_filter.yaml")
        self.compare_yaml_content(expected_ss_path, "actual_search_space.yaml")


if __name__ == "__main__":
    unittest.main(buffer=True)
