#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for run command
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
import os
import unittest
import unittest.mock as mock
import yaml
from configparser import ConfigParser
from autotuner.main import run_main
from autotuner.tuners.simple_tuner import SimpleTuner
from autotuner.yamlmanager import YAMLManager
from opentuner import Result
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


class TestAutotunerRun(unittest.TestCase):
    """
    Test the 'run' subcommand in autotuner
    """

    def setUp(self):
        self.args = mock.MagicMock()
        self.args.list_tuners = False
        self.args.list_techniques = False
        self.args.command = "run"
        curr_dir = os.path.dirname(__file__)
        self.args.config_file = os.path.join(
            curr_dir, "Inputs", "test_sample.ini")
        self.args.search_space = os.path.join(
            curr_dir, "Inputs", "run", "search_space_loop_only.yaml")
        self.args.tuner = None
        self.args.output = None

        self.test_configuration_data = {
            '1PeelCount': 0,
            '1UnrollCount': 8,
            '1MachineScheduling': 1,
            '1VectorizationInterleave': 4,
            '1ForceTargetMaxVectorInterleaveFactor': 4,
            '1OptPass': 2,
            '2PeelCount': 1,
            '2UnrollCount': 8,
            '2VectorizationInterleave': 4,
            '2MachineScheduling': 4,
            '2ForceTargetMaxVectorInterleaveFactor': 2,
            '2OptPass': 1,
            '3PeelCount': 0,
            '3UnrollCount': 4,
            '3VectorizationInterleave': 2,
            '3MachineScheduling': 2,
            '3DummyIntParam': 2,
            '4PeelCount': 0,
            '4UnrollCount': 1,
            '4VectorizationInterleave': 4,
            '4DummyFloatParam': 4.563,
            '5PeelCount': 0,
            '5UnrollCount': 1,
            '5VectorizationInterleave': 2,
            '6PeelCount': 0,
            '6UnrollCount': 2,
            '6VectorizationInterleave': 4,
        }

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

    def test_build_llvm_input(self):
        """
        Check LLVM input can be successfully and correctly generated
        """
        search_space = os.path.join(os.path.dirname(__file__), "Inputs",
                                    "run", "search_space.yaml")
        yaml_manager = YAMLManager()
        task_map = yaml_manager.parse_search_space(search_space)
        yaml_manager.build_llvm_input(self.test_configuration_data, task_map,
                                      "actual_llvm_input.yaml", None)

        expected_llvm_input_path = os.path.join(os.path.dirname(
            __file__), "Outputs/run/llvm_input.yaml")
        self.compare_yaml_content(expected_llvm_input_path,
                                  "actual_llvm_input.yaml")

    def test_build_llvm_input_loop_only(self):
        search_space = os.path.join(os.path.dirname(__file__), "Inputs",
                                    "run", "search_space_loop_only.yaml")
        yaml_manager = YAMLManager()
        task_map = yaml_manager.parse_search_space(search_space)
        yaml_manager.build_llvm_input(self.test_configuration_data, task_map,
                                      "actual_llvm_input.yaml", None)

        expected_llvm_input_path = os.path.join(os.path.dirname(
            __file__), "Outputs/run/llvm_input_loop_only.yaml")
        self.compare_yaml_content(expected_llvm_input_path,
                                  "actual_llvm_input.yaml")

    def test_build_llvm_input_mbb_only(self):
        search_space = os.path.join(os.path.dirname(__file__), "Inputs",
                                    "run", "search_space_mbb_only.yaml")
        yaml_manager = YAMLManager()
        task_map = yaml_manager.parse_search_space(search_space)
        yaml_manager.build_llvm_input(self.test_configuration_data, task_map,
                                      "actual_llvm_input.yaml", None)

        expected_llvm_input_path = os.path.join(os.path.dirname(
            __file__), "Outputs/run/llvm_input_mbb_only.yaml")
        self.compare_yaml_content(expected_llvm_input_path,
                                  "actual_llvm_input.yaml")

    def test_build_llvm_input_function_only(self):
        search_space = os.path.join(os.path.dirname(__file__), "Inputs",
                                    "run", "search_space_function_only.yaml")
        yaml_manager = YAMLManager()
        task_map = yaml_manager.parse_search_space(search_space)
        yaml_manager.build_llvm_input(self.test_configuration_data, task_map,
                                      "actual_llvm_input.yaml", None)

        expected_llvm_input_path = os.path.join(os.path.dirname(
            __file__), "Outputs/run/llvm_input_function_only.yaml")
        self.compare_yaml_content(expected_llvm_input_path,
                                  "actual_llvm_input.yaml")

    def test_build_llvm_input_module_only(self):
        search_space = os.path.join(os.path.dirname(__file__), "Inputs",
                                    "run", "search_space_module_only.yaml")
        yaml_manager = YAMLManager()
        task_map = yaml_manager.parse_search_space(search_space)
        yaml_manager.build_llvm_input(self.test_configuration_data, task_map,
                                      "actual_llvm_input.yaml", None)

        expected_llvm_input_path = os.path.join(os.path.dirname(
            __file__), "Outputs/run/llvm_input_module_only.yaml")
        self.compare_yaml_content(expected_llvm_input_path,
                                  "actual_llvm_input.yaml")

    @mock.patch("autotuner.main._parse_common_options")
    @mock.patch("autotuner.main.issubclass")
    def test_run_main_called_tuner(self, mock_issubclass,
                                   mock_parse_common_options):
        """
        Check if tuner.main is called
        """
        # issubclass won't work with the mock object, so we need to mock it
        mock_issubclass.return_value = False
        tuner = mock.MagicMock()
        config = ConfigParser()
        config.optionxform = str
        config["DEFAULT"]["ConfigFilePath"] = os.path.abspath(
            os.path.dirname(self.args.config_file))
        config.read(self.args.config_file)

        mock_parse_common_options.return_value = (tuner, config)
        run_main(self.args)

        tuner.main.assert_called_once()

    @mock.patch.object(SimpleTuner, "call_program")
    @mock.patch.object(SimpleTuner, "_print_errors")
    def test_simpletuner_call_program(self, mock_print_errors,
                                      mock_call_program):
        """
        Check if call_program function is called
        """
        mock_call_program.return_value = {"returncode": 0, "time": 10}
        tuner = SimpleTuner(self.args, None, None,
                            self.args.search_space, None, "some run_dir",
                            "some run_cmd")
        result = tuner.run(None, None, None)

        mock_call_program.assert_called_once_with(
            "some run_cmd", cwd="some run_dir", limit=120)
        self.assertIsInstance(result, Result)

        mock_print_errors.assert_not_called()

    @mock.patch.object(SimpleTuner, "call_program")
    @mock.patch.object(SimpleTuner, "_print_errors")
    def test_simpletuner_nonzero_returncode(self, mock_print_errors,
                                            mock_call_program):
        """
        Check correct error handling when call_program returns non-zero
        """
        mock_call_program.return_value = {"returncode": 1, "time": 10}
        tuner = SimpleTuner(self.args, None, None,
                            self.args.search_space, None, "some run_dir",
                            "some run_cmd")
        result = tuner.run(None, None, None)

        mock_call_program.assert_called_once_with(
            "some run_cmd", cwd="some run_dir", limit=120)
        self.assertIsInstance(result, Result)

        mock_print_errors.assert_called()


if __name__ == "__main__":
    unittest.main(buffer=True)
