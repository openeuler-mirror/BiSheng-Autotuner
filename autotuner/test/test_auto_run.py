#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for auto_run command
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
import os
from io import StringIO
import unittest
import unittest.mock as mock
from opentuner import MeasurementInterface
from autotuner.iomanager import EmptySearchSpaceError
from autotuner.main import auto_run_main
from autotuner.tuners.simple_tuner import SimpleTuner


class TestAutoRun(unittest.TestCase):
    """
    Test the auto_run subcommand in autotuner
    """

    def setUp(self):
        self.args = mock.MagicMock()
        self.args.list_tuners = False
        self.args.list_techniques = False
        self.args.command = "run"
        curr_dir = os.path.dirname(__file__)
        self.args.config_file = os.path.join(
            curr_dir, "Inputs", "test_sample.ini")
        self.args.tuner = None
        self.args.output = None
        self.args.stage_order = ["loop"]
        self.args.search_config_file = os.path.join(
            curr_dir, "Inputs", "test_search_space_config.yaml")

    @mock.patch.object(MeasurementInterface, "call_program")
    @mock.patch.object(SimpleTuner, "main")
    @mock.patch("autotuner.main.create_io_manager")
    @mock.patch("autotuner.main._clean_opp")
    def test_phase_based_run_main_iomanager_called(self,
                                                   mock_clean_opp,
                                                   mock_create_io_manager,
                                                   mock_simpletuner_main,
                                                   mock_call_program):
        mock_iomanager = mock.MagicMock()
        mock_create_io_manager.return_value = mock_iomanager

        fake_result = {"returncode": 0,
                       "stdout": "succuss", "stderr": "",
                       'timeout': False, 'time': 1.89}
        mock_call_program.return_value = fake_result

        auto_run_main(self.args)

        mock_create_io_manager.assert_called_once()
        mock_iomanager.generate_search_space.assert_called_once()

    @mock.patch.object(MeasurementInterface, "call_program")
    @mock.patch.object(SimpleTuner, "main")
    @mock.patch("autotuner.main.create_io_manager")
    @mock.patch("autotuner.main._clean_opp")
    def test_phase_based_run_main_subprocess_called(self,
                                                    mock_clean_opp,
                                                    mock_create_io_manager,
                                                    mock_simpletuner_main,
                                                    mock_call_program):
        """
        Check if the subprocess that calls compiler command
        is called in auto_run
        """
        mock_iomanager = mock.MagicMock()
        mock_create_io_manager.return_value = mock_iomanager

        fake_result = {"returncode": 0,
                       "stdout": "succuss", "stderr": "",
                       'timeout': False, 'time': 1.89}
        mock_call_program.return_value = fake_result

        auto_run_main(self.args)

        mock_call_program.assert_called_once()

    @mock.patch.object(MeasurementInterface, "call_program")
    @mock.patch.object(SimpleTuner, "main")
    @mock.patch("autotuner.main.create_io_manager")
    @mock.patch("autotuner.main._clean_opp")
    def test_phase_based_run_main_tuner_called(self,
                                               mock_clean_opp,
                                               mock_create_io_manager,
                                               mock_simpletuner_main,
                                               mock_call_program):
        """
        Check if simple tuner's main function is called
        """
        mock_iomanager = mock.MagicMock()
        mock_create_io_manager.return_value = mock_iomanager

        fake_result = {"returncode": 0,
                       "stdout": "succuss", "stderr": "",
                       'timeout': False, 'time': 1.89}
        mock_call_program.return_value = fake_result

        auto_run_main(self.args)

        mock_clean_opp.assert_called()
        mock_simpletuner_main.assert_called_once()

    @mock.patch.object(MeasurementInterface, "call_program")
    @mock.patch.object(SimpleTuner, "main")
    @mock.patch("autotuner.main.create_io_manager")
    @mock.patch("autotuner.main._clean_opp")
    def test_phase_based_run_main_multi_stage(self, mock_clean_opp,
                                              mock_create_io_manager,
                                              mock_simpletuner_main,
                                              mock_call_program):
        """
        Check correct behaviour when tuning with multi-stage
        """
        mock_iomanager = mock.MagicMock()
        mock_create_io_manager.return_value = mock_iomanager

        fake_result = {"returncode": 0,
                       "stdout": "succuss", "stderr": "",
                       'timeout': False, 'time': 1.89}
        mock_call_program.return_value = fake_result

        self.args.stage_order = [
            "other", "function", "loop", "machine_basic_block"]

        auto_run_main(self.args)

        mock_create_io_manager.assert_called_once()
        self.assertEqual(mock_call_program.call_count, 4)
        self.assertEqual(mock_iomanager.generate_search_space.call_count, 4)
        self.assertEqual(mock_simpletuner_main.call_count, 4)

    @mock.patch.object(MeasurementInterface, "call_program")
    @mock.patch.object(SimpleTuner, "main")
    @mock.patch("autotuner.main.create_io_manager")
    @mock.patch("autotuner.main._clean_opp")
    def test_phase_based_run_main_subprocess_failed(self, mock_clean_opp,
                                                    mock_create_io_manager,
                                                    mock_simpletuner_main,
                                                    mock_call_program):
        mock_iomanager = mock.MagicMock()
        mock_create_io_manager.return_value = mock_iomanager

        fake_result = {"returncode": 1,
                       "stdout": "", "stderr": "some error",
                       'timeout': False, 'time': -1}
        mock_call_program.return_value = fake_result

        auto_run_main(self.args)

        mock_iomanager.generate_search_space.assert_not_called()
        mock_simpletuner_main.assert_not_called()

    @mock.patch.object(MeasurementInterface, "call_program")
    @mock.patch.object(SimpleTuner, "main")
    @mock.patch("autotuner.main.create_io_manager")
    @mock.patch("autotuner.main._clean_opp")
    @mock.patch("sys.stdout", new_callable=StringIO)
    def test_phase_based_run_main_empty_searchspace_error(
        self, mock_stdout,
        mock_clean_opp,
        mock_create_io_manager,
        mock_simpletuner_main,
        mock_call_program
    ):
        mock_iomanager = mock.MagicMock()
        mock_create_io_manager.return_value = mock_iomanager

        fake_result = {"returncode": 0,
                       "stdout": "succuss", "stderr": "",
                       'timeout': False, 'time': 1.89}
        mock_call_program.return_value = fake_result

        mock_simpletuner_main.side_effect = EmptySearchSpaceError()

        auto_run_main(self.args)

        # Check correct error msg is printed
        self.assertTrue(
            "Empty search space, stop the current stage" in
            mock_stdout.getvalue(), "Correct EmptySearchSpaceError " \
                                    "msg not printed")
        mock_simpletuner_main.assert_called_once()

    @mock.patch.object(MeasurementInterface, "call_program")
    @mock.patch.object(SimpleTuner, "main")
    @mock.patch("autotuner.main.create_io_manager")
    @mock.patch("autotuner.main._clean_opp")
    @mock.patch("sys.stdout", new_callable=StringIO)
    def test_phase_based_run_main_multi_stage_with_error(
        self, mock_stdout,
        mock_clean_opp,
        mock_create_io_manager,
        mock_simpletuner_main,
        mock_call_program
    ):
        mock_iomanager = mock.MagicMock()
        mock_create_io_manager.return_value = mock_iomanager

        fake_result = {"returncode": 0,
                       "stdout": "succuss", "stderr": "",
                       'timeout': False, 'time': 1.89}
        mock_call_program.return_value = fake_result

        self.args.stage_order = ["function", "loop"]
        # The first stage result in error
        mock_simpletuner_main.side_effect = [EmptySearchSpaceError(), None]

        auto_run_main(self.args)

        # Check correct error msg is printed
        self.assertTrue(
            "Empty search space, stop the current stage" in
            mock_stdout.getvalue(), "Correct EmptySearchSpaceError "
                                    "msg not printed")
        self.assertEqual(mock_simpletuner_main.call_count, 2)


if __name__ == "__main__":
    unittest.main(buffer=True)
