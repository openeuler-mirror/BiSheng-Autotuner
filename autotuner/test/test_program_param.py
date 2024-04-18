#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Test the program-param code region in AutoTuner
# Copyright (C) 2017-2022, Huawei Technologies Co., Ltd. All rights reserved.
"""
Test the program-param code region in AutoTuner
"""

import os
import shutil
import subprocess
import unittest
import tempfile
import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from autotuner.remarkparser import AutoTuning


class TestAutoTunerProgramParam(unittest.TestCase):
    """
    Test the program-param code region in AutoTuner.
    """
    def setUp(self):
        self.autotuner_dir = ""
        self.data_dir = ""

    def compare_yaml_content(self, expected_yaml_path, actual_yaml_path):
        """
        Compare two yaml files by their contents using pyyaml
        """
        with open(expected_yaml_path) as expected_stream, open(
                actual_yaml_path) as actual_stream:
            for expected_remark in yaml.load_all(expected_stream,
                                                 Loader=Loader):
                actual_remark = yaml.load_all(actual_stream, Loader=Loader)
                self.assertTrue(
                    expected_remark in actual_remark,
                    "Generated Yaml is different from expected."
                )
                actual_stream.seek(0)


    def check_formated_yaml(self):
        """
        checking:
            llvm-param: different for different files
            program-param: same for different files
        """
        program_param_args_list = None
        program_param_args_list_temp = None

        llvm_param_args_list = None
        llvm_param_args_list_temp = None

        check_program_param = True
        check_llvm_param = True

        with open(os.path.join(self.data_dir, "formated_config.yaml"), 'r') as file:
            config_dic = yaml.load_all(file, Loader=yaml.FullLoader)
            for code_region in config_dic:
                if code_region['CodeRegionType'] == "program-param":
                    if program_param_args_list is None:
                        program_param_args_list = code_region['Args']
                    else:
                        program_param_args_list_temp = code_region['Args']
                        check_program_param &= (program_param_args_list == program_param_args_list_temp)
                if code_region['CodeRegionType'] == "llvm-param":
                    if llvm_param_args_list is None:
                        llvm_param_args_list = code_region['Args']
                    else:
                        llvm_param_args_list_temp = code_region['Args']
                        check_llvm_param &= (llvm_param_args_list == llvm_param_args_list_temp)
        return check_program_param, check_llvm_param


    def test_default_compiler_options(self):
        """
        Test AutoTuner uses the default options to initialize the search space
        for program-param and llvm-param code regions when '--use-baseline-config'
        is provided.
        """
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        self.autotuner_dir = os.path.join(curr_dir, "..", "..", "bin")
        input_dir = os.path.join(curr_dir, "Inputs", "program_param_opp")
        search_space_file = os.path.join(
            curr_dir, "Inputs", "search_space_config", "search_space_baseline.yaml"
        )
        llvm_autotuner_bin = os.path.join(self.autotuner_dir, "llvm-autotune")

        data_dir = tempfile.TemporaryDirectory()
        os.environ["AUTOTUNE_DATADIR"] = data_dir.name
        opp_dir = os.path.join(data_dir.name, "opp")
        shutil.copytree(input_dir, opp_dir)

        cmd = [
            llvm_autotuner_bin,
            "minimize",
            "-b",
            "--search-space",
            search_space_file,
        ]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)

        expected_config = os.path.join(
            curr_dir, "Outputs", "baseline", "config_baseline.yaml"
        )
        generated_config = os.path.join(data_dir.name, "config.yaml")
        self.compare_yaml_content(generated_config, expected_config)

        data_dir.cleanup()


    def test_program_param(self):
        """
        Test the program-param code region in AutoTuner.
        Firstly, run autotuner with llvm-autotune minimize
        Secondly, checking llvm-param and program-param code region within config.yaml
        """
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        self.autotuner_dir = os.path.join(curr_dir, "..", "..", "bin")
        input_dir = os.path.join(curr_dir, "Inputs", "program_param_opp")
        search_space_file = os.path.join(curr_dir, "..", "search_space_config", "extended_search_space.yaml")
        llvm_autotune_bin = os.path.join(self.autotuner_dir, "llvm-autotune")

        data_dir = tempfile.TemporaryDirectory()
        self.data_dir = data_dir.name
        os.environ['AUTOTUNE_DATADIR'] = data_dir.name
        opp_dir = os.path.join(self.data_dir, 'opp')
        shutil.copytree(input_dir, opp_dir)

        cmd = [llvm_autotune_bin, "minimize", "--deterministic=True", "--search-space", search_space_file]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)

        with open(os.path.join(self.data_dir, "config.yaml"), 'r') as infile, \
        open(os.path.join(self.data_dir, "formated_config.yaml"), 'w') as outfile:
            data = infile.read()
            data = data.replace("!AutoTuning", "")
            outfile.write(data)

        check_program_param, check_llvm_param = self.check_formated_yaml()

        self.assertTrue(check_program_param)
        self.assertFalse(check_llvm_param)

        data_dir.cleanup()

if __name__ == "__main__":
    unittest.main(buffer=True)
