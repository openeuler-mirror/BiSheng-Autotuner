#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Autotuner's utility functions.
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""

import os
import stat
import tempfile
import unittest
import unittest.mock as mock

from autotuner.utils import parse_feedback_file
from autotuner.utils import create_secure_fd
from autotuner.utils import check_file_permissions


class TestUtils(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_file = os.path.join(self.temp_dir.name, "test.csv")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_feedback_file_not_found(self):
        with self.assertRaises(IOError):
            parse_feedback_file(self.temp_file)

    def test_parse_feedback_file_empty(self):
        with open(self.temp_file, "w") as file:
            file.write("")
        numbers = parse_feedback_file(self.temp_file)
        self.assertEqual([], numbers)

    def test_parse_feedback_single_num(self):
        with open(self.temp_file, "w") as file:
            file.write("1")
        numbers = parse_feedback_file(self.temp_file)
        self.assertEqual([1], numbers)

    def test_parse_feedback_multi_num(self):
        with open(self.temp_file, "w") as file:
            file.write("1,2,3,4,5,6")
        numbers = parse_feedback_file(self.temp_file)
        self.assertEqual([1, 2, 3, 4, 5, 6], numbers)

    def test_parse_feedback_multi_lines(self):
        with open(self.temp_file, "w") as file:
            file.write("1,2,3,4,5,6 \n")
            file.write("7,8,9")
        numbers = parse_feedback_file(self.temp_file)
        self.assertEqual([1, 2, 3, 4, 5, 6, 7, 8, 9], numbers)

    def test_parse_feedback_invalid_value(self):
        with open(self.temp_file, "w") as file:
            file.write("a")
        with self.assertRaises(IOError):
            parse_feedback_file(self.temp_file)

    def test_parse_feedback_invalid_value_mix(self):
        with open(self.temp_file, "w") as file:
            file.write("1,2,3,a")
        with self.assertRaises(IOError):
            parse_feedback_file(self.temp_file)

    def test_parse_feedback_invalid_value_space(self):
        with open(self.temp_file, "w") as file:
            file.write("1,2,3 a")
        with self.assertRaises(IOError):
            parse_feedback_file(self.temp_file)


    @mock.patch("logging.Logger.info")
    def test_file_permissions(self, mock_logger):
        """
        Test secure file creation and file permission verification process.
        """
        file_fd = create_secure_fd(self.temp_file)

        # File permissions are not tested for Windows OS; a log message is shown instead.
        if os.name == "nt":
            check_file_permissions(self.temp_file)
            mock_logger.assert_called_with(
                "File permissions are not verified for Windows OS."
            )
            os.close(file_fd)
            return

        # Verify if correct permissions are applied.
        try:
            check_file_permissions(self.temp_file)
        except IOError:
            self.fail("check_file_permissions() raise IOError unexpectedly.")

        # Adding write permission for 'Group' which will raise IOError.
        modes = stat.S_IWUSR | stat.S_IRUSR | stat.S_IWGRP
        os.chmod(self.temp_file, modes)
        with self.assertRaises(IOError):
            check_file_permissions(self.temp_file)


if __name__ == '__main__':
    unittest.main()
