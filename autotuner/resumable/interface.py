# coding=utf-8
"""
Resumable Autotuner Interface.
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
import glob
import logging
import os
import random
import types
import dill as pickle # Use dill because it supports lambda functions.

from autotuner.dbutils import create_config_db_session
from autotuner.iomanager import EmptySearchSpaceError
from autotuner.iomanagerutils import create_io_manager
from autotuner.resumable.run_manager import ResumableRunManager
from autotuner.utils import create_secure_fd
from autotuner.utils import check_file_permissions
from opentuner import ConfigurationManipulator
from opentuner import resultsdb
from opentuner import Result
from opentuner.measurement.interface import DefaultMeasurementInterface
from opentuner.measurement.inputmanager import FixedInputManager
from opentuner.search.objective import MinimizeTime
from opentuner.search.objective import MaximizeRate

log = logging.getLogger(__name__)


class AutoTunerState:
    """
    A representation of the state of a tuning run that can be saved/resumed to/
    from disk.
    """

    def __init__(self, args, data_dir, objective):
        args.database = file_exists_error_or_path(data_dir, "autotuner.db")
        self.iomanager = create_io_manager(args.parse_format)
        self.args = args
        self.opp_dir = os.path.join(data_dir, "opp")
        self.config_file = file_exists_error_or_path(data_dir, "config" +
                                                     self.iomanager.
                                                     get_file_extension())
        self.objective = objective
        self.root_technique = None
        self.pending_result_callbacks = None
        self.use_prev_configs = False
        self.inject_seed = False
        self.best_result = None

        if args.use_optimal_configs != "none" \
            and not args.use_hash_matching:
            args.use_optimal_configs = "none"
            log.warning("'use-hash-matching' must be enabled to use previous "
                        "optimal configuration! Disabling reuse/retune.")

        if args.use_optimal_configs == "reuse":
            self.use_prev_configs = True
        elif args.use_optimal_configs == "retune":
            self.use_prev_configs = True
            self.inject_seed = True

        if "CONFIG_DB_DIR" in os.environ:
            self.config_db_dir = os.environ["CONFIG_DB_DIR"]
        else:
            self.config_db_dir = data_dir
            log.warning("Environment variable CONFIG_DB_DIR is not set; "
                        "a default directory is used for saving the "
                        "config database: %s", self.config_db_dir)
        # Always create config_db since program-params need it.
        self.config_db = create_config_db_session(self.config_db_dir)

        # Init search space.
        search_space = self._init_search_space()
        try:
            self.task_map = self.iomanager.parse_search_space(search_space,
                                self.args.use_dynamic_values,
                                self.args.use_baseline_config,
                                os.path.join(data_dir, "initial_config.json"))
        except EmptySearchSpaceError:
            # We found the optimal configurations in database for every
            # code region.
            self.iomanager.generate_baseline_llvm_input(self.config_file,
                                                        self.config_db)
            log.info("Optimal conditions are found for this code and wrote "
                     "optimal configuration to %s; re-compile with -fautotune "
                     "to apply it", self.config_file)
            log.info("Please use --use-optimal-configs=none to tune the code "
                     "from scratch or use --use-optimal-configs=retune to "
                     "retune the code and use the optimal configurations as "
                     "starting point (seed value) for the AutoTuner.")
            raise

        if self.args.use_baseline_config:
            self.args.seed_configuration.append(os.path.join(data_dir,
                                                    "initial_config.json"))
            log.info("Baseline configuration used as input seed.")

        if self.inject_seed:
            # Use optimal configuration from condif_db for code regions if
            # found otherwise assign random values and store the seed baseline
            # in 'initial_config.json' and forward its path to OpenTuner.
            # This file will act as initial seed configurations for OpenTuner.
            seed_config = self.iomanager.seed_baseline(self.task_map,
                self.config_db, os.path.join(data_dir, "initial_config.json"))
            self.args.seed_configuration.append(seed_config)
            log.info("Seed configuration injected to the AutoTuner.")

        self.manipulator = self._init_manipulator()
        self.current_desired_result_ids = []
        self.tuning_run_id = None
        self.random_state = None

    def __getstate__(self):
        state = self.__dict__.copy()
        if state['config_db']:
            state['config_db'].commit()
            state['config_db'].close()
        state['config_db'] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        # Since introducing program-param, config_db is always created.
        self.config_db = create_config_db_session(self.config_db_dir)
        # Do not re-seed if the state is being loaded.
        self.args.seed_configuration = []


    def _init_search_space(self):
        if not self.args.search_space:
            dir_name = os.path.dirname(__file__)
            search_space_config = os.path.join(
                dir_name,
                "../search_space_config/default_search_space" +
                self.iomanager.get_file_extension())
        else:
            search_space_config = self.args.search_space
        check_file_permissions(search_space_config)

        opp_files = glob.glob(os.path.join(self.opp_dir, "*"))
        if len(opp_files) == 0:
            raise Exception(
                "No tuning opportunities files under {}; compile with "
                "-fautotune-generate to generate tuning opportunities".format(
                    self.opp_dir))

        search_space = self.iomanager.generate_search_space(
            opp_files, search_space_config,
            file_name_filter=self.args.file_name_filter,
            func_name_filter=self.args.func_name_filter,
            name_filter=self.args.name_filter,
            type_filter=self.args.type_filter,
            pass_filter=self.args.pass_filter,
            config_db=self.config_db,
            use_hash_matching=self.args.use_hash_matching,
            use_prev_configs=self.use_prev_configs,
            inject_seed=self.inject_seed)

        # Clean up the tuning opportunity files since they are no longer needed
        # after the search space is generated.
        files = glob.glob(self.opp_dir + "/*")
        _remove_files(files)

        return search_space

    def _init_manipulator(self):
        manipulator = ConfigurationManipulator()
        for _, task in self.task_map.items():
            for param in task.param_list:
                manipulator.add_parameter(param)
        return manipulator


class StateSerializer:
    """
    This class manages serialization of a AutoTunerState.
    """

    def __init__(self, data_dir, state_file="state.p"):
        self.data_dir = data_dir
        self.state_file = state_file

    def check_state_exists(self):
        file_exists_error_or_path(self.data_dir, self.state_file)

    def serialize(self, auto_tuner):
        auto_tuner_state = auto_tuner.auto_tuner_state
        # Add extra necessary information into AutoTunerState.
        auto_tuner_state.root_technique = \
            auto_tuner.api.search_driver.root_technique
        pending_results = [
            result
            for result in auto_tuner.api.search_driver.pending_result_callbacks
            if type(result[1]) != types.FunctionType
        ]
        auto_tuner_state.pending_result_callbacks = pending_results
        auto_tuner_state.random_state = random.getstate()

        file_path = os.path.join(self.data_dir, self.state_file)
        file_fd = create_secure_fd(file_path)
        with os.fdopen(file_fd, 'wb') as file:
            pickle.dump(auto_tuner_state, file)

    def deserialize(self):
        file_path = os.path.join(self.data_dir, self.state_file)
        check_file_permissions(file_path)
        with open(file_path, "rb") as file:
            auto_tuner_state = pickle.load(file)
        random.setstate(auto_tuner_state.random_state)
        return auto_tuner_state


class AutoTunerInterface:
    """
    A representation of AutoTuner's command line interface.
    """

    def __init__(self):
        self.auto_tuner_state = None
        self.api = None

    def initialize(self, args, data_dir, objective):
        self.auto_tuner_state = AutoTunerState(args, data_dir, objective)
        self.process_deterministic(args, data_dir)
        interface = self._create_default_measurement_interface(
            self.auto_tuner_state)
        self.api = ResumableRunManager(interface, self.auto_tuner_state.args)
        self.auto_tuner_state.tuning_run_id = self.api.tuning_run.id
        log.info("Initialized a new tuning run (ID: %s)",
                 self.api.tuning_run.id)

    def resume(self, auto_tuning_state):
        self.auto_tuner_state = auto_tuning_state
        interface = self._create_default_measurement_interface(
            auto_tuning_state)
        self.api = ResumableRunManager(interface, auto_tuning_state.args,
                                       auto_tuning_state)
        log.info("Resumed a tuning run (ID: %s)", self.api.tuning_run.id)

    def next_config(self, trials=1, retry_limit=5):
        """
        Generate an Auto-tuning config file that should be tested with LLVM
        next.
        """
        self.auto_tuner_state.current_desired_result_ids.clear()
        for trial_id in range(trials):
            desired_result = self.api.get_next_desired_result()
            retry_count = 1
            # Sometimes search techniques can't avoid producing duplicates,
            # and therefore result in returning None.
            # We should retry it until the limit.
            while desired_result is None and retry_count <= retry_limit:
                desired_result = self.api.get_next_desired_result()
                retry_count += 1
            # If search space is very small, sometimes the techniques
            # have trouble finding a config that hasn't already been tested.
            # Give a warning and make it try again.
            if desired_result is None:
                log.warning(
                    "Possible configurations may have been exhausted; "
                    "try again or run 'llvm-autotune finalize' to generate "
                    "optimal configuration")
                log.warning("Only %s configurations were generated",
                            trial_id)
                # Save the current desired_results into the database.
                self.api.commit(force=True)
                return
            cfg = desired_result.configuration.data
            if trials == 1:
                file_name = self.auto_tuner_state.config_file
            else:
                index = self.auto_tuner_state.config_file.find('.yaml')
                file_name = "{}-{}{}".format(
                                    self.auto_tuner_state.config_file[:index],
                                    trial_id,
                                    self.auto_tuner_state.config_file[index:])

            self.auto_tuner_state.iomanager.build_llvm_input(
                cfg, self.auto_tuner_state.task_map, file_name,
                config_db=self.auto_tuner_state.config_db,
                use_hash_matching=self.auto_tuner_state.args.use_hash_matching)

            log.info("Generated a new configuration (ID: %s)",
                     desired_result.id)

            # Save state info into the auto_tuning_state.
            self.auto_tuner_state.current_desired_result_ids.append(
                desired_result.id)

        # Save the best_result (found so far) for initialization of SearchDriver
        # object.
        self.auto_tuner_state.best_result = self.api.search_driver.best_result

        # Save the current desired_results into the database.
        self.api.commit(force=True)

    def feedback(self, feedback_values):
        """
        Report the performance feedback.
        """
        desired_result_ids = self.auto_tuner_state.current_desired_result_ids
        if len(feedback_values) != len(desired_result_ids):
            log.error("Number of feedback values received: %s",
                      len(feedback_values))
            log.error("Number of feedback values expected: %s",
                      len(desired_result_ids))
            raise Exception("Number of feedback values do not match the number"
                            " of configurations generated in the "
                            "previous iteration")

        for trial_id, feedback in enumerate(feedback_values):
            if self.auto_tuner_state.objective == "maximize":
                # Since time is required for Result() as an attribute,
                # but never used for the objective MaximizeRate,
                # leave it as 0.
                result = Result(rate=feedback, time=0)
            else:
                result = Result(time=feedback)

            current_desired_result = self.api.session.query(
                resultsdb.models.DesiredResult).get(
                desired_result_ids[trial_id])
            self.api.report_result(current_desired_result,
                                   result)
            log.info("Received performance feedback %f for "
                     "configuration (ID: %s)", feedback,
                     desired_result_ids[trial_id])
        self.api.commit(force=True)

        # Clean up config files from the previous iteration.
        files = glob.glob(self.auto_tuner_state.config_file + "*")
        _remove_files(files)

    def dump(self, config_update=False):
        """
        Dump the best config without terminating the tuning run.

        Args:
            config_update: Specifying if the optimal conditions (found) will "
            "be stored in database for re-using. It will overwrite the "
            "existing configurations; if any."

        Returns:
            True if best configuration is available or False otherwise.
        """
        self.api.search_driver = self._process_all_results()

        best_cfg = self.api.get_best_configuration()
        if best_cfg:
            if self.auto_tuner_state.objective == "maximize":
                best_performance = self.api.search_driver.best_result.rate
            else:
                best_performance = self.api.search_driver.best_result.time
            log.info("Best performance feedback is %s", best_performance)

            hash_option = self.auto_tuner_state.args.use_hash_matching
            if config_update and self.auto_tuner_state.config_db:
                self.auto_tuner_state.iomanager.update_config_db(
                    best_cfg, self.auto_tuner_state.task_map,
                    config_db=self.auto_tuner_state.config_db,
                    use_hash_matching=hash_option)
            self.auto_tuner_state.iomanager.build_llvm_input(
                best_cfg, self.auto_tuner_state.task_map,
                self.auto_tuner_state.config_file,
                config_db=self.auto_tuner_state.config_db,
                use_hash_matching=hash_option)

            log.info("Wrote optimal configuration to %s; re-compile with "
                     "-fautotune to apply it",
                     self.auto_tuner_state.config_file)

            return True
        else:
            log.warning("Optimal configuration has not yet been found")
            return False

    def finalize(self, config_update):
        """
        Finalize the tuning run and save the best config.
        """
        if self.dump(config_update):
            self.api.finish()
            if self.auto_tuner_state.config_db:
                self.auto_tuner_state.config_db.commit()
                self.auto_tuner_state.config_db.close()
            log.info("Finalized a tuning run (ID: %s)",
                     self.auto_tuner_state.tuning_run_id)
        else:
            raise Exception("Cannot finalize without an optimal configuration")

    @staticmethod
    def _create_default_measurement_interface(auto_tuning_state):
        if auto_tuning_state.objective == "minimize":
            objective = MinimizeTime()
        elif auto_tuning_state.objective == "maximize":
            objective = MaximizeRate()
        else:
            raise Exception(
                "Unsupported objective: {}".format(
                    auto_tuning_state.objective))

        interface = DefaultMeasurementInterface(
            args=auto_tuning_state.args,
            objective=objective,
            input_manager=FixedInputManager(),
            manipulator=auto_tuning_state.manipulator,
            project_name='unnamed_project',
            program_name='unnamed_program',
            program_version='0.1')
        return interface

    @staticmethod
    def process_deterministic(args, data_dir):
        """
        This function performs following two tasks.
        1.  Saving random state in 'data_dir/random_state.seed' file during
            initialization.
        2.  Use seed value or seed file to set the random state and initialize
            the search space deterministically; if enabled.
        """
        if args.deterministic:
            if args.seed_file:
                file_path = args.seed_file
                check_file_permissions(file_path)
                with open(file_path, "rb") as file:
                    random_state = pickle.load(file)
                    random.setstate(random_state)
            else:
                random.seed(args.seed)

        random_state = random.getstate()
        file_path = os.path.join(data_dir, "random_state.seed")
        file_fd = create_secure_fd(file_path)
        with os.fdopen(file_fd, 'wb') as file:
            pickle.dump(random_state, file)

    def _process_all_results(self):
        search_driver = self.api.search_driver
        search_driver.new_results = []
        results_query = search_driver.results_query()
        for result in results_query.order_by(Result.collection_date):
            search_driver.plugin_proxy.on_result(result)
            search_driver.new_results.append(result)
            if search_driver.best_result is None:
                search_driver.best_result = result
                result.was_new_best = True
            elif search_driver.objective.lt(result, search_driver.best_result):
                search_driver.best_result = result
                search_driver.was_new_best = True
                search_driver.plugin_proxy.on_new_best_result(result)
            else:
                result.was_new_best = False
        search_driver.result_callbacks()
        return search_driver


def file_exists_error_or_path(data_dir, filename):
    file_path = os.path.join(data_dir, filename)
    if os.path.exists(file_path):
        raise IOError(
            "Existing autotuner data found {}; "
            "set AUTOTUNER_DATADIR environment variable "
            "to a new directory".format(file_path))
    return file_path


def _remove_files(files):
    try:
        for ele in files:
            if os.path.isfile(ele):
                os.remove(ele)
    except Exception as error:
        log.warning(error)
