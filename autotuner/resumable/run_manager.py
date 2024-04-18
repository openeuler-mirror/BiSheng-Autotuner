# coding=utf-8
"""
A resumable RunManager that manages a tuning run.
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
import logging

from opentuner import resultsdb
from opentuner.api import TuningRunManager
from opentuner.resultsdb.models import Base as DBModel


class ResumableRunManager(TuningRunManager):
    """
    This class manages a tuning run that can save/resumed to/from disk.
    """

    def __init__(self, measurement_interface, args, tuning_state=None,
                 **kwargs):
        if not tuning_state:
            # Initialize a new run manager.
            super(ResumableRunManager, self).__init__(measurement_interface,
                                                      args,
                                                      **kwargs)
        else:
            # Initialize a new run manager with the existing tuning state.
            super(TuningRunManager, self).__init__(measurement_interface, args,
                                                   **kwargs)
            self.engine, self.Session = resultsdb.connect(
                tuning_state.args.database)
            # Resume the tuning run from the database
            self.tuning_run = self.session.query(
                resultsdb.models.TuningRun).get(tuning_state.tuning_run_id)
            if self.tuning_run.state != "RUNNING":
                raise Exception(
                    "Cannot resume a complete or aborted tuning run; "
                    "run 'llvm-autotune minimize/maximize' to start "
                    "a new tuning run")
            driver_kwargs = {
                'args': self.args,
                'best_result': self.attach_db_session(tuning_state.best_result),
                'input_manager': self.input_manager,
                'manipulator': self.manipulator,
                'measurement_interface': self.measurement_interface,
                'objective': self.objective,
                'session': self.session,
                'tuning_run_main': self,
                'tuning_run': self.tuning_run,
                'extra_seeds':
                    self.measurement_interface.seed_configurations(),
                'extra_criteria':
                    self.measurement_interface.extra_convergence_criteria,
                'root_technique': self.attach_db_session(
                    tuning_state.root_technique)
            }
            self.search_driver = self.search_driver_cls(**driver_kwargs)
            self.search_driver.pending_result_callbacks = \
                self.attach_db_session(tuning_state.pending_result_callbacks)

            self.measurement_driver = self.measurement_driver_cls(
                **driver_kwargs)
            self.measurement_interface.set_driver(self.measurement_driver)
            self.input_manager.set_driver(self.measurement_driver)

            self.tuning_run.machine_class = self.measurement_driver. \
                get_machine_class()
            self.tuning_run.input_class = self.input_manager.get_input_class()

            # Suppress logs from opentuner modules.
            logging.getLogger("opentuner").setLevel(logging.CRITICAL)

    def attach_db_session(self, obj):
        """
        Find database instances recursively and attach a new session with them.
        """
        if obj is None:
            return obj

        if isinstance(obj, DBModel):
            # session.merge() examines the primary key attributes of the source
            # instance and attempts to reconcile it with an instance of the
            # same primary key in the session.
            obj = self.session.merge(obj)
        elif isinstance(obj, dict):
            new_dict = dict()
            for key, value in obj.items():
                new_dict[self.attach_db_session(
                    key)] = self.attach_db_session(value)
            obj = new_dict
        elif isinstance(obj, list):
            obj = [self.attach_db_session(ele) for ele in obj]
        elif isinstance(obj, tuple):
            obj = tuple([self.attach_db_session(ele) for ele in obj])
        elif hasattr(obj, "__dict__"):
            for key in obj.__dict__:
                value = obj.__dict__[key]
                obj.__dict__[key] = self.attach_db_session(value)
        return obj
