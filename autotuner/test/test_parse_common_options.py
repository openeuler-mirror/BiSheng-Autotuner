#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for _parse_common_options
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
import os
import unittest
import unittest.mock as mock
from autotuner.main import _parse_common_options
from autotuner.tuners.tunerbase import CustomTunerBase


class TestParseCommonOptions(unittest.TestCase):
    """
    Test the functionality of _parse_common_options in main.py
    """

    def setUp(self):
        self.args = mock.MagicMock()
        self.args.list_tuners = False
        self.args.list_techniques = False
        self.args.command = "run"
        curr_dir = os.path.dirname(__file__)
        self.args.config_file = os.path.join(
            curr_dir, "Inputs", "test_sample.ini")
        self.args.search_space = True
        self.args.tuner = False
        self.args.output = False

    @mock.patch("autotuner.tuners.tunerbase.get_available_tuners")
    def test_list_tuners(self, mock_get_available_tuners):
        """
        Test the --list-tuner flag for autotuner
        """
        self.args.list_tuners = True
        self.args.plugin_dir = "some path"
        mock_get_available_tuners.return_value = "some tuners"

        with self.assertRaises(SystemExit) as context:
            _parse_common_options(self.args)
        self.assertEqual(context.exception.code, 0)

    def test_no_config_file(self):
        self.args.config_file = None

        with self.assertRaises(SystemExit) as context:
            _parse_common_options(self.args)
        self.assertEqual(context.exception.code, 1)

    def test_no_search_space_file(self):
        self.args.search_space = None

        with self.assertRaises(SystemExit) as context:
            _parse_common_options(self.args)
        self.assertEqual(context.exception.code, 1)

    def test_config_file_wrong_path(self):
        self.args.config_file = "some incorrect path"
        self.assertRaises(IOError, _parse_common_options, self.args)

    def test_config_file_env_var(self):
        """
        Test if the env variables in config file can be defined
        """
        _parse_common_options(self.args)
        self.assertIsNotNone(os.getenv("TestEnvVar"))

    def test_config_file_correct_setting(self):
        """
        Test if the settings in config can be applied
        """
        _, config = _parse_common_options(self.args)
        expected_compile_dir = os.path.abspath(os.path.dirname(self.args.config_file))
        self.assertEqual(config["Compiling Setting"]["CompileDir"],
                         expected_compile_dir)

    def test_tuner_and_plugin(self):
        """
        Test --tuner and --plugin flag for autotuner
        """
        self.args.tuner = "dummy_tuner"
        self.args.plugin_dir = os.path.dirname(__file__)

        tuner, _ = _parse_common_options(self.args)
        self.assertTrue(issubclass(tuner, CustomTunerBase),
                      "Sample test tuner usage failed. Plugin or " \
                      "tuners are not well implemented")


if __name__ == "__main__":
    unittest.main(buffer=True)
