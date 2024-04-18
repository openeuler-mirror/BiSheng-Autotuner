#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Autotuner's yaml manager for resumable interface.
Copyright (C) 2022-2022, Huawei Technologies Co., Ltd. All rights reserved.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
import unittest.mock as mock
import yaml

from autotuner.yamlmanager import YAMLManager
from autotuner import yamlmanager
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


class YAMLTest(unittest.TestCase):
    def setUp(self):
        self.args = mock.MagicMock()
        # Create a temp directory for every test.
        self.temp_dir = tempfile.TemporaryDirectory()
        self.args.output = os.path.join(self.temp_dir.name, "actual_output.yaml")
        self.args.search_config_file = os.path.join(
            os.path.dirname(__file__),
            "Inputs",
            "parse",
            "test_search_space_config.yaml",
        )

    def tearDown(self):
        # Clean temp directory after every tests.
        self.temp_dir.cleanup()


    def cmp_files(self, expected_path, actual_path):
        line1 = line2 = True
        with open(expected_path, "r") as f1, open(actual_path, "r") as f2:
            while line1 and line2:
                line1 = f1.readline()
                line2 = f2.readline()
                if line1 != line2:
                    return False
        return True


    def test_parse_dynamic_options(self):
        """
        Test to handle dynamic values retrieved from the new generated
        search_space.  This test in particular tests new changes to
        parse_search_space().
        """
        search_space_file = os.path.join(
            os.path.dirname(__file__),
            "Inputs",
            "region_pruning",
            "loop_small_meta.yaml",
        )
        yaml_manager = YAMLManager()
        search_space = yaml_manager.generate_search_space(
            [search_space_file], self.args.search_config_file)
        with open(self.args.output, 'w') as f:
            yaml.dump(search_space, f, sort_keys = False)

        expected = os.path.join(
            os.path.dirname(__file__), "Outputs", "yaml", "dynamic_options.yaml"
        )
        self.compare_yaml_content(expected, self.args.output)


    def test_parse_multiple_param(self):
        """
        Test to handle multiple dynamic values retrieved from
        clang -fautotune-generate.
        This test in particular tests new changes to _generate_search_space().
        """
        self.args.opp_file = [
            os.path.join(
                os.path.dirname(__file__), "Inputs", "opp", "multiple_param.yaml"
            )
        ]

        YAMLManager().generate_search_space_file(self.args.opp_file,
                                                 self.args.output,
                                                 self.args.search_config_file)

        expected_ss_path = os.path.join(
            os.path.dirname(__file__),
            "Outputs",
            "yaml",
            "search_space_multiple_param.yaml",
        )

        self.compare_yaml_content(expected_ss_path, self.args.output)


    def compare_yaml_content(self, expected_yaml_path, actual_yaml_path):
        """
        Compare two yaml files by their contents using pyyaml.
        """
        try:
            with open(expected_yaml_path) as expected_stream, open(
                    actual_yaml_path) as actual_stream:
                actual_generator = yaml.load_all(actual_stream,
                                                 Loader=Loader)
                for expected_dict in yaml.load_all(expected_stream,
                                                   Loader=Loader):
                    actual_dict = next(actual_generator)
                    self.assertEqual(
                        expected_dict, actual_dict, "Parsed result yaml "
                        "different from expected")
                # expected has finished, check whether actual finished too
                # if the actual_generator still has content, then fail
                self.assertRaises(StopIteration, next, actual_generator)
        finally:
            os.unlink(actual_yaml_path)


    def test_parse_baseline_configs(self):
        """
        Test to handle baseline values retrieved from the generated search_space
        This test in particular tests new changes to parse_search_space()
        """
        search_space_file = os.path.join(
            os.path.dirname(__file__), "Inputs", "opp", "baseline.yaml"
        )
        yaml_manager = YAMLManager()
        search_space = yaml_manager.generate_search_space(
            [search_space_file], self.args.search_config_file)
        yaml_manager.parse_search_space(search_space, False, True, self.args.output)

        expected = os.path.join(
            os.path.dirname(__file__), "Outputs", "yaml", "baseline_init.json"
        )
        self.assertTrue(self.cmp_files(expected, self.args.output))


    def test_yaml_dump(self):
        """
        Verify that each code region is dumped on a single line.
        """
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        autotuner_dir = os.path.join(curr_dir, "..", "..", "bin")
        input_dir = os.path.join(curr_dir, "Inputs", "opp")
        data_dir = tempfile.TemporaryDirectory()
        os.environ["AUTOTUNE_DATADIR"] = data_dir.name

        opp_dir = os.path.join(data_dir.name, "opp/")
        os.mkdir(opp_dir)
        shutil.copyfile(
            os.path.join(input_dir, "core_list_join.c.yaml"),
            os.path.join(opp_dir, "core_list_join.c.yaml"),
        )

        # Run AutoTuner to process opportunity files and generate config.yaml.
        cmd = [os.path.join(autotuner_dir, "llvm-autotune"), "minimize"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)

        num_code_regions = 0
        num_lines = 0
        with open(os.path.join(data_dir.name, "config.yaml")) as ifile:
            # Count number of code regions in config.yaml file.
            num_code_regions = len([s for s in ifile.readlines() if "AutoTuning" in s])
            ifile.seek(0)
            # Count number of lines in config.yaml file which have some text.
            num_lines = sum(1 for s in ifile.readlines() if len(s) > 0)

        # Number of code regions must be equal to number of lines (with text).
        self.assertEqual(num_code_regions, num_lines)
        data_dir.cleanup()


if __name__ == "__main__":
    unittest.main(buffer=True)
