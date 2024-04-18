#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test to run AutoTuner in deterministic manner
Copyright (C) 2017-2022, Huawei Technologies Co., Ltd. All rights reserved.
"""
import os
import shutil
import subprocess
import unittest
import filecmp
import tempfile
from sqlalchemy import create_engine
from sqlalchemy import text

from autotuner.models import CodeRegion


class TestAutoTunerPruning(unittest.TestCase):
    """
    This class tests code regions pruning using IR hashing. It also tests
    storing of optimal configurations in database and reusing them.
    First 5 tests verify the functionality for the opportunity files with
    meta data while the last 5 tests verify the functionality for the
    opportunity files with no meta data.
    """

    @classmethod
    def setUpClass(self):
        # Setting environment. This method will run once at start.
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        self.autotuner_dir = os.path.join(curr_dir, "..", "..", "bin")
        self.input_dir = os.path.join(curr_dir, "Inputs", "region_pruning")
        self.backup_dir = tempfile.TemporaryDirectory()
        self.data_dir = tempfile.TemporaryDirectory()
        os.environ["AUTOTUNE_DATADIR"] = self.data_dir.name

    def setUp(self):
        os.mkdir(self.data_dir.name + "/opp")

    def tearDown(self) -> None:
        # Cleanup: This method will execute after every test.
        if os.path.exists(os.path.join(self.data_dir.name, "configs.db")):
            shutil.copyfile(
                os.path.join(self.data_dir.name, "configs.db"),
                os.path.join(self.backup_dir.name, "configs.db"),
            )

        for entry in os.listdir(self.data_dir.name):
            full_entry = os.path.join(self.data_dir.name, entry)
            if os.path.isdir(full_entry) and not os.path.islink(full_entry):
                shutil.rmtree(full_entry)
            else:
                os.remove(full_entry)

        if os.path.exists(os.path.join(self.backup_dir.name, "configs.db")):
            shutil.copyfile(
                os.path.join(self.backup_dir.name, "configs.db"),
                os.path.join(self.data_dir.name, "configs.db")
            )
        return super().tearDown()


    def db_validator(self):
        num_current_code_regions = 0
        num_optimal_configs = 0
        num_seen = 0
        eng = create_engine(
            "sqlite:///" + os.path.join(self.data_dir.name, "configs.db")
        )
        con = eng.raw_connection()

        for line in con.iterdump():
            if line.startswith('INSERT INTO "optimalConfigs"'):
                num_optimal_configs += 1
            if line.startswith('INSERT INTO "currentCodeRegions"'):
                num_current_code_regions += 1
                if line[-3] == '1':
                    num_seen += 1

        return num_current_code_regions, num_seen, num_optimal_configs


    def test_loop_meta_0(self):
        # Testing without new features.
        if os.path.exists(os.path.join(self.data_dir.name, "configs.db")):
            os.unlink(os.path.join(self.data_dir.name, "configs.db"))
        if os.path.exists(os.path.join(self.backup_dir.name, "configs.db")):
            os.unlink(os.path.join(self.backup_dir.name, "configs.db"))
        shutil.copyfile(
            os.path.join(self.input_dir, "loop_meta.yaml"),
            os.path.join(self.data_dir.name, "opp", "loop_meta.yaml"),
        )

        cmd = [os.path.join(self.autotuner_dir, "llvm-autotune"), "minimize"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)
        cmd = [os.path.join(self.autotuner_dir, "llvm-autotune"), "feedback", "15"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)
        cmd = [os.path.join(self.autotuner_dir, "llvm-autotune"), "feedback" "14"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)
        cmd = [os.path.join(self.autotuner_dir, "llvm-autotune"), "finalize"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)

        current_code_regions, _, _ = self.db_validator()
        self.assertTrue(os.path.exists(os.path.join(self.data_dir.name, "configs.db")))
        self.assertEqual(current_code_regions, 0)


    def test_loop_meta_1(self):
        # Using hashing and storing optimal configurations.
        # parameters used: use-hash-matching, store-optimal-configs
        shutil.copyfile(
            os.path.join(self.input_dir, "loop_small_meta.yaml"),
            os.path.join(self.data_dir.name, "opp", "loop_small_meta.yaml"),
        )

        cmd = [
            os.path.join(self.autotuner_dir, "llvm-autotune"),
            "minimize",
            "--use-hash-matching",
        ]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)
        cmd = [os.path.join(self.autotuner_dir, "llvm-autotune"), "feedback", "15"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)
        cmd = [os.path.join(self.autotuner_dir, "llvm-autotune"), "feedback" "14"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)
        cmd = [
            os.path.join(self.autotuner_dir, "llvm-autotune"),
            "finalize",
            "--store-optimal-configs",
        ]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)

        shutil.copyfile(
            os.path.join(self.data_dir.name, "config.yaml"),
            os.path.join(self.backup_dir.name, "config.yaml"),
        )

        current_code_regions, seen, optimal_configs = self.db_validator()

        self.assertTrue(os.path.exists(os.path.join(self.data_dir.name, "configs.db")))
        self.assertEqual(current_code_regions, 8)
        self.assertEqual(seen, 0)
        self.assertEqual(optimal_configs, 8)

    def test_loop_meta_2(self):
        # Testing reusing of optimal configurations for re-tuning. As all the
        # code regions are stored in database (previous test case), so the new
        # config.yaml file will be same as the config.yaml file from previous
        # test case.
        # parameters used: use-hash-matching, use-optimal-configs retune
        shutil.copyfile(
            os.path.join(self.input_dir, "loop_small_meta.yaml"),
            os.path.join(self.data_dir.name, "opp", "loop_small_meta.yaml"),
        )

        cmd = [
            os.path.join(self.autotuner_dir, "llvm-autotune"),
            "minimize",
            "--use-hash-matching",
            "--use-optimal-configs=retune",
        ]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)

        self.assertTrue(
            filecmp.cmp(
                os.path.join(self.data_dir.name, "config.yaml"),
                os.path.join(self.backup_dir.name, "config.yaml"),
            )
        )

    def test_loop_meta_3(self):
        # Testing resuing of optimal configuration. If all the code regions
        # have optimal configurations in configs.db then Empty Serch Space
        # will be generated and config.yaml file will be created with optimal
        # configurations found.
        # parameter used: use-hash-matching, use-optimal-configs reuse
        shutil.copyfile(
            os.path.join(self.input_dir, "loop_small_meta.yaml"),
            os.path.join(self.data_dir.name, "opp", "loop_small_meta.yaml"),
        )

        cmd = [
            os.path.join(self.autotuner_dir, "llvm-autotune"),
            "minimize",
            "--use-hash-matching",
            "--use-optimal-configs=reuse",
        ]
        if os.name == "nt":
            cmd.insert(0, "py")
        out = subprocess.run(cmd, stderr=subprocess.PIPE).stderr.decode()

        self.assertIn("empty search space", out)


    def test_loop_meta_4(self):
        # Testing the IR hashing and reusing of optimal configurations.
        # AutoTuner will tune the program if there are other code regions
        # in addition to the code regions in optimal configurations table.
        # parameters used: use-hash-matching, use-optimal-configs reuse
        shutil.copyfile(
            os.path.join(self.input_dir, "loop_meta.yaml"),
            os.path.join(self.data_dir.name, "opp", "loop_meta.yaml"),
        )

        cmd = [
            os.path.join(self.autotuner_dir, "llvm-autotune"),
            "minimize",
            "--use-hash-matching",
            "--use-optimal-configs=reuse",
        ]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)
        cmd = [os.path.join(self.autotuner_dir, "llvm-autotune"), "feedback", "15"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)
        cmd = [os.path.join(self.autotuner_dir, "llvm-autotune"), "feedback", "14"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)
        cmd = [os.path.join(self.autotuner_dir, "llvm-autotune"), "finalize"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)

        current_code_regions, seen, optimal_configs = self.db_validator()

        self.assertTrue(os.path.exists(os.path.join(self.data_dir.name, "configs.db")))
        self.assertEqual(current_code_regions, 38)
        self.assertEqual(seen, 23)
        self.assertEqual(optimal_configs, 8)


    def test_loop_nometa_0(self):
        # Testing without new features.
        if os.path.exists(os.path.join(self.data_dir.name, "configs.db")):
            os.unlink(os.path.join(self.data_dir.name, "configs.db"))
        if os.path.exists(os.path.join(self.backup_dir.name, "configs.db")):
            os.unlink(os.path.join(self.backup_dir.name, "configs.db"))
        shutil.copyfile(
            os.path.join(self.input_dir, "loop_nometa.yaml"),
            os.path.join(self.data_dir.name, "opp", "loop_nometa.yaml"),
        )

        cmd = [os.path.join(self.autotuner_dir, "llvm-autotune"), "minimize"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)
        cmd = [os.path.join(self.autotuner_dir, "llvm-autotune"), "feedback", "15"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)
        cmd = [os.path.join(self.autotuner_dir, "llvm-autotune"), "feedback", "14"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)
        cmd = [os.path.join(self.autotuner_dir, "llvm-autotune"), "finalize"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)

        current_code_regions, _, _ = self.db_validator()
        self.assertTrue(os.path.exists(os.path.join(self.data_dir.name, "configs.db")))
        self.assertEqual(current_code_regions, 0)


    def test_loop_nometa_1(self):
        # Using hashing and storing optimal configurations.
        # parameters used: use-hash-matching, store-optimal-configs
        shutil.copyfile(
            os.path.join(self.input_dir, "loop_small_nometa.yaml"),
            os.path.join(self.data_dir.name, "opp", "loop_small_nometa.yaml"),
        )

        cmd = [
            os.path.join(self.autotuner_dir, "llvm-autotune"),
            "minimize",
            "--use-hash-matching",
        ]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)
        cmd = [os.path.join(self.autotuner_dir, "llvm-autotune"), "feedback", "15"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)
        cmd = [os.path.join(self.autotuner_dir, "llvm-autotune"), "feedback", "14"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)
        cmd = [
            os.path.join(self.autotuner_dir, "llvm-autotune"),
            "finalize",
            "--store-optimal-configs",
        ]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)

        shutil.copyfile(
            os.path.join(self.data_dir.name, "config.yaml"),
            os.path.join(self.backup_dir.name, "config.yaml"),
        )

        current_code_regions, seen, optimal_configs = self.db_validator()

        self.assertTrue(os.path.exists(os.path.join(self.data_dir.name, "configs.db")))
        self.assertEqual(current_code_regions, 8)
        self.assertEqual(seen, 0)
        self.assertEqual(optimal_configs, 8)

    def test_loop_nometa_2(self):
        # Testing reusing of optimal configurations for re-tuning. As all the
        # code regions are stored in database (previous test case), so the new
        # config.yaml file will be same as the config.yaml file from previous
        # test case.
        # parameters used: use-hash-matching, use-optimal-configs retune
        shutil.copyfile(
            os.path.join(self.input_dir, "loop_small_nometa.yaml"),
            os.path.join(self.data_dir.name, "opp", "loop_small_nometa.yaml"),
        )

        cmd = [
            os.path.join(self.autotuner_dir, "llvm-autotune"),
            "minimize",
            "--use-hash-matching",
            "--use-optimal-configs=retune",
        ]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)

        self.assertTrue(
            filecmp.cmp(
                os.path.join(self.data_dir.name, "config.yaml"),
                os.path.join(self.backup_dir.name, "config.yaml"),
            )
        )

    def test_loop_nometa_3(self):
        # Testing resuing of optimal configuration. If all the code regions
        # have optimal configurations in configs.db then Empty Serch Space
        # will be generated and config.yaml file will be created with optimal
        # configurations found.
        # parameters used: use-hash-matching, use-optimal-configs reuse
        shutil.copyfile(
            os.path.join(self.input_dir, "loop_small_nometa.yaml"),
            os.path.join(self.data_dir.name, "opp", "loop_small_nometa.yaml"),
        )

        cmd = [
            os.path.join(self.autotuner_dir, "llvm-autotune"),
            "minimize",
            "--use-hash-matching",
            "--use-optimal-configs=reuse",
        ]
        if os.name == "nt":
            cmd.insert(0, "py")
        out = subprocess.run(cmd, stderr=subprocess.PIPE).stderr.decode()

        self.assertIn("empty search space", out)


    def test_loop_nometa_4(self):
        # Testing the IR hashing and reusing of optimal configurations.
        # AutoTuner will tune the program if there are other code regions
        # in addition to the code regions in optimal configurations table.
        # parameters used: use-hash-matching, use-optimal-configs reuse
        shutil.copyfile(
            os.path.join(self.input_dir, "loop_nometa.yaml"),
            os.path.join(self.data_dir.name, "opp", "loop_nometa.yaml"),
        )

        cmd = [
            os.path.join(self.autotuner_dir, "llvm-autotune"),
            "minimize",
            "--use-hash-matching",
            "--use-optimal-configs=reuse",
        ]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)
        cmd = [os.path.join(self.autotuner_dir, "llvm-autotune"), "feedback", "15"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)
        cmd = [os.path.join(self.autotuner_dir, "llvm-autotune"), "feedback" "14"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)
        cmd = [os.path.join(self.autotuner_dir, "llvm-autotune"), "finalize"]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)

        current_code_regions, seen, optimal_configs = self.db_validator()

        self.assertTrue(os.path.exists(os.path.join(self.data_dir.name, "configs.db")))
        self.assertEqual(current_code_regions, 16)
        self.assertEqual(seen, 7)
        self.assertEqual(optimal_configs, 8)


    def test_code_region_attributes(self):
        """
        Testing database 'config.db' to ensure that all of the attributes of
        CodeRegion are added in to the database and 'config.yaml' will be
        generated with all the required fields when hashing based pruning is
        applied on the code regions (which is used to reduce search space).
        """

        # Creating search space and initializing 'config.db' database.
        shutil.copyfile(
            os.path.join(self.input_dir, "loop_small_meta.yaml"),
            os.path.join(self.data_dir.name, "opp", "loop_small_meta.yaml"),
        )

        cmd = [
            os.path.join(self.autotuner_dir, "llvm-autotune"),
            "minimize",
            "--use-hash-matching",
            "--use-optimal-configs=reuse",
        ]
        if os.name == "nt":
            cmd.insert(0, "py")
        subprocess.run(cmd, stderr=subprocess.DEVNULL)

        # Creating a dummy CodeRegion to determine the fields of this class
        # dynamically and removing 'debug_loc' as config.db stores the debug
        # location as three columns (debug_file, debug_line, and debug_column).
        dummy = CodeRegion("loop_unrool", "dummy", "dummy_func", "loop")
        config_fields = list(dummy.__dict__.keys())
        config_fields.remove("debug_loc")

        # Creating connection with 'config.db' and extracting the column names.
        eng = create_engine(
            "sqlite:///" + os.path.join(self.data_dir.name, "configs.db")
        )
        conn = eng.connect()
        result = conn.execute(text("select * from currentCodeRegions"))

        # Comparing 'CodeRegion' fields with 'config.db' columns
        self.assertTrue(all(elem in result.keys() for elem in config_fields))

if __name__ == "__main__":
    unittest.main(buffer=True)
