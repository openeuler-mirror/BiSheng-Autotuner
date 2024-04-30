#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Autotuner's resumable interface.
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
import os
import unittest
import unittest.mock as mock

from autotuner.resumable.interface import AutoTunerState
from autotuner.resumable.interface import AutoTunerInterface
from autotuner.resumable.interface import file_exists_error_or_path
from autotuner.yamlmanager import YAMLManager


class TestAutoRun(unittest.TestCase):
    """
    Test Autotuner's resumable interface.
    """

    def setUp(self):
        self.data_dir = "dummy_dir"
        self.args = mock.MagicMock()
        self.args.parse_format = "yaml"
        self.args.use_hash_matching = False
        self.args.deterministic = False
        self.objective = "minimize"
        self.auto_tuner = AutoTunerInterface()

    @mock.patch("autotuner.resumable.interface.create_config_db_session")
    @mock.patch.object(AutoTunerInterface, "process_deterministic")
    @mock.patch("autotuner.resumable.interface.ResumableRunManager")
    @mock.patch.object(AutoTunerState, "_init_search_space")
    @mock.patch.object(YAMLManager, "parse_search_space")
    def test_interface_initialize(self, mock_parse_search_space,
                                  mock_init_search_space,
                                  mock_rusumable_run_manager,
                                  mock_process_deterministic,
                                  mock_create_config_db_session):
        # Mock ResumableRunManager()
        mock_api = mock.MagicMock()
        mock_api.tuning_run.id = 1
        mock_rusumable_run_manager.return_value = mock_api
        mock_create_config_db_session.return_value = 'sqlite:///' + os.path.join(self.data_dir, "configs.db")

        # Call AutoTunerInterface.initialize
        self.auto_tuner.initialize(self.args, self.data_dir, self.objective)

        # Check if ResumableRunManager constructor is called.
        mock_rusumable_run_manager.assert_called_once_with(mock.ANY, self.args)

        # Check if a new AutoTunerState populated properly.
        mock_init_search_space.assert_called_once()
        self.assertEqual(self.auto_tuner.auto_tuner_state.tuning_run_id, 1)
        self.assertEqual(self.auto_tuner.auto_tuner_state.opp_dir,
                         os.path.join("dummy_dir", "opp"))
        self.assertEqual(self.auto_tuner.auto_tuner_state.config_file,
                         os.path.join("dummy_dir", "config.yaml"))
        self.assertEqual(
            self.auto_tuner.auto_tuner_state.current_desired_result_ids, [])

    @mock.patch("autotuner.resumable.interface.create_config_db_session")
    @mock.patch("autotuner.resumable.interface.ResumableRunManager")
    @mock.patch.object(AutoTunerState, "_init_search_space")
    @mock.patch.object(YAMLManager, "parse_search_space")
    def test_interface_resume(self, mock_parse_search_space,
                              mock_init_search_space,
                              mock_rusumable_run_manager,
                              mock_create_config_db_session):
        mock_create_config_db_session.return_value = 'sqlite:///' + os.path.join(self.data_dir, "configs.db")
        auto_tuner_state = AutoTunerState(self.args, self.data_dir,
                                          self.objective)
        auto_tuner_state.tuning_run_id = 3

        self.auto_tuner.resume(auto_tuner_state)
        # Check if ResumableRunManager constructor is called with correct
        # arguments.
        mock_rusumable_run_manager.assert_called_once_with(mock.ANY, self.args,
                                                           auto_tuner_state)
        # Check if the AutoTunerState resumed.
        self.assertIs(auto_tuner_state, self.auto_tuner.auto_tuner_state)

    @mock.patch("autotuner.resumable.interface.create_config_db_session")
    @mock.patch.object(AutoTunerState, "_init_search_space")
    @mock.patch.object(YAMLManager, "parse_search_space")
    @mock.patch.object(YAMLManager, "build_llvm_input")
    @mock.patch.object(YAMLManager, "create_dummy_llvm_input")
    def test_interface_next_config(self, mock_build_llvm_input,
                                   mock_parse_search_space,
                                   mock_init_search_space,
                                   mock_create_dummy_llvm_input,
                                   mock_create_config_db_session):
        # Setup steps for the AutoTunerInterface that is resumed already.
        mock_create_config_db_session.return_value = 'sqlite:///' + os.path.join(self.data_dir, "configs.db")
        auto_tuner_state = AutoTunerState(self.args, self.data_dir,
                                          self.objective)
        self.auto_tuner.auto_tuner_state = auto_tuner_state
        # Mock api to avoid database connections.
        mock_api = mock.MagicMock()
        mock_desired_result = mock.MagicMock()
        mock_desired_result.configuration.data = None
        mock_desired_result.id = 5
        mock_api.get_next_desired_result.return_value = mock_desired_result
        self.auto_tuner.api = mock_api

        # Before the first call to next_config().
        self.assertEqual(
            self.auto_tuner.auto_tuner_state.current_desired_result_ids, [])
        self.auto_tuner.next_config()
        # After the first call to next_config().
        # Check if current_desired_result_ids is updated after the call.
        self.assertEqual(
            self.auto_tuner.auto_tuner_state.current_desired_result_ids, [5])

        # Before the second call to next_config().
        mock_desired_result.id = 6
        self.assertEqual(
            self.auto_tuner.auto_tuner_state.current_desired_result_ids, [5])
        self.auto_tuner.next_config()
        # After the second call to next_config().
        # Check if current_desired_result_ids is updated after the call.
        self.assertEqual(
            self.auto_tuner.auto_tuner_state.current_desired_result_ids, [6])

    @mock.patch("autotuner.resumable.interface.create_config_db_session")
    @mock.patch.object(AutoTunerState, "_init_search_space")
    @mock.patch.object(YAMLManager, "parse_search_space")
    @mock.patch.object(YAMLManager, "build_llvm_input")
    @mock.patch.object(YAMLManager, "create_dummy_llvm_input")
    def test_interface_next_config_multi_trials(self, mock_build_llvm_input,
                                                   mock_parse_search_space,
                                                   mock_init_search_space,
                                                   mock_create_dummy_llvm_input,
                                                   mock_create_config_db_session):
        # Setup steps for the AutoTunerInterface that is resumed already.
        mock_create_config_db_session.return_value = 'sqlite:///' + os.path.join(self.data_dir, "configs.db")
        auto_tuner_state = AutoTunerState(self.args, self.data_dir,
                                          self.objective)
        self.auto_tuner.auto_tuner_state = auto_tuner_state
        # Mock api to avoid database connections.
        mock_api = mock.MagicMock()
        mock_desired_result = mock.MagicMock()
        mock_desired_result.configuration.data = None
        mock_desired_result.id = 5
        mock_api.get_next_desired_result.return_value = mock_desired_result
        self.auto_tuner.api = mock_api

        # Before the first call to next_config().
        self.assertEqual(
            self.auto_tuner.auto_tuner_state.current_desired_result_ids, [])
        # Call next_config with 3 trials.
        self.auto_tuner.next_config(3)
        # After the first call to next_config().
        # Check if current_desired_result_ids is updated after the call.
        self.assertEqual(
            self.auto_tuner.auto_tuner_state.current_desired_result_ids,
            [5, 5, 5])

        # Before the second call to next_config().
        mock_desired_result.id = 6
        self.assertEqual(
            self.auto_tuner.auto_tuner_state.current_desired_result_ids,
            [5, 5, 5])
        # Call next_config with 4 trials.
        self.auto_tuner.next_config(4)
        # After the second call to next_config().
        # Check if current_desired_result_ids is updated after the call.
        self.assertEqual(
            self.auto_tuner.auto_tuner_state.current_desired_result_ids,
            [6, 6, 6, 6])

    @mock.patch("autotuner.resumable.interface.create_config_db_session")
    @mock.patch("autotuner.resumable.interface.Result")
    @mock.patch.object(AutoTunerState, "_init_search_space")
    @mock.patch.object(YAMLManager, "parse_search_space")
    def test_interface_feedback(self, mock_parse_search_space,
                                mock_init_search_space,
                                mock_result,
                                mock_create_config_db_session):
        # Setup steps for the AutoTunerInterface that is resumed already.
        mock_create_config_db_session.return_value = 'sqlite:///' + os.path.join(self.data_dir, "configs.db")
        auto_tuner_state = AutoTunerState(self.args, self.data_dir,
                                          self.objective)
        auto_tuner_state.current_desired_result_ids = [1]
        self.auto_tuner.auto_tuner_state = auto_tuner_state
        # Mock api to avoid database connections.
        self.auto_tuner.api = mock.MagicMock()

        self.auto_tuner.feedback([50])
        # By default the objective is minimize.
        # Check if a Result object it created created properly.
        mock_result.assert_called_once_with(time=50)
        # Check if the the following functions are called.
        self.auto_tuner.api.session.query.assert_called()
        self.auto_tuner.api.report_result.assert_called_once()
        self.auto_tuner.api.commit.assert_called_once()

        # Change the objective to maximize.
        self.auto_tuner.auto_tuner_state.objective = "maximize"

        self.auto_tuner.feedback([60])
        # Since the objective is maximize, check if a Result object is
        # created properly.
        mock_result.assert_called_with(time=0, rate=60)

    @mock.patch("autotuner.resumable.interface.create_config_db_session")
    @mock.patch("autotuner.resumable.interface.Result")
    @mock.patch.object(AutoTunerState, "_init_search_space")
    @mock.patch.object(YAMLManager, "parse_search_space")
    def test_interface_feedback_multi_trials(self, mock_parse_search_space,
                                mock_init_search_space,
                                mock_result,
                                mock_create_config_db_session):
        # Setup steps for the AutoTunerInterface that is resumed already.
        mock_create_config_db_session.return_value = 'sqlite:///' + os.path.join(self.data_dir, "configs.db")
        auto_tuner_state = AutoTunerState(self.args, self.data_dir,
                                          self.objective)
        self.auto_tuner.auto_tuner_state = auto_tuner_state
        auto_tuner_state.current_desired_result_ids = [1, 2]
        # Mock API to avoid database connections.
        self.auto_tuner.api = mock.MagicMock()

        # Feedback numbers for two trials.
        self.auto_tuner.feedback([50, 60])
        # By default the objective is minimize.
        # Check if a Result object has been created created properly.
        mock_result.assert_any_call(time=50)
        mock_result.assert_any_call(time=60)
        # Check if the the following functions are called.
        self.auto_tuner.api.session.query.assert_called()
        self.auto_tuner.api.report_result.assert_called()
        self.auto_tuner.api.commit.assert_called_once()

        # Change # of trials to 4.
        auto_tuner_state.current_desired_result_ids = [1, 2, 3, 4]
        self.auto_tuner.feedback([15, 20, 25, 30])
        mock_result.assert_any_call(time=15)
        mock_result.assert_any_call(time=20)
        mock_result.assert_any_call(time=25)
        mock_result.assert_any_call(time=30)

    @mock.patch("autotuner.resumable.interface.create_config_db_session")
    @mock.patch("autotuner.resumable.interface.Result")
    @mock.patch.object(AutoTunerState, "_init_search_space")
    @mock.patch.object(YAMLManager, "parse_search_space")
    def test_interface_feedback_exceptions(self, mock_parse_search_space,
                                           mock_init_search_space,
                                           mock_result,
                                           mock_create_config_db_session):
        # Setup steps for the AutoTunerInterface that is resumed already.
        mock_create_config_db_session.return_value = 'sqlite:///' + os.path.join(self.data_dir, "configs.db")
        auto_tuner_state = AutoTunerState(self.args, self.data_dir,
                                          self.objective)

        self.auto_tuner.auto_tuner_state = auto_tuner_state
        # Mock api to avoid database connections.
        self.auto_tuner.api = mock.MagicMock()

        # Calling feedback before initialization should raise an exception.
        auto_tuner_state.current_desired_result_ids = []
        with self.assertRaises(Exception):
            self.auto_tuner.feedback([50])
            self.auto_tuner.api.commit.assert_not_called()

        # Feeding back more numbers than expected should raise an exception.
        auto_tuner_state.current_desired_result_ids = [1]
        with self.assertRaises(Exception):
            self.auto_tuner.feedback([50, 60])
            self.auto_tuner.api.commit.assert_not_called()

        # Feeding back fewer numbers than expected should raise an exception.
        auto_tuner_state.current_desired_result_ids = [1, 2, 3]
        with self.assertRaises(Exception):
            self.auto_tuner.feedback([50, 60])
            self.auto_tuner.api.commit.assert_not_called()

    @mock.patch("autotuner.resumable.interface.create_config_db_session")
    @mock.patch.object(AutoTunerInterface, "_process_all_results")
    @mock.patch.object(AutoTunerState, "_init_search_space")
    @mock.patch.object(YAMLManager, "parse_search_space")
    @mock.patch.object(YAMLManager, "build_llvm_input")
    def test_interface_dump(self, mock_build_llvm_input,
                            mock_parse_search_space,
                            mock_init_search_space,
                            mock_process_all_results,
                            mock_create_config_db_session):
        # Setup steps for the AutoTunerInterface that is resumed already.
        mock_create_config_db_session.return_value = 'sqlite:///' + os.path.join(self.data_dir, "configs.db")
        auto_tuner_state = AutoTunerState(self.args, self.data_dir,
                                          self.objective)
        self.auto_tuner.auto_tuner_state = auto_tuner_state
        # Mock API to avoid database connections.
        self.auto_tuner.api = mock.MagicMock()

        # Check if the best config is dumped successfully.
        self.auto_tuner.api.get_best_configuration.return_value = \
            mock.MagicMock()
        self.assertTrue(self.auto_tuner.dump())
        # Check if dump() returns false if no best config found.
        self.auto_tuner.api.get_best_configuration.return_value = None
        self.assertFalse(self.auto_tuner.dump())

    @mock.patch("autotuner.resumable.interface.os.path.exists")
    def test_file_exists_error_or_path(self, mock_exists):
        mock_exists.return_value = True
        self.assertRaises(IOError, file_exists_error_or_path, "data_dir",
                          "data_file")
        mock_exists.return_value = False
        self.assertEqual(
            os.path.join("data_dir", "data_file"),
            file_exists_error_or_path("data_dir", "data_file"),
        )


if __name__ == "__main__":
    unittest.main(buffer=True)
